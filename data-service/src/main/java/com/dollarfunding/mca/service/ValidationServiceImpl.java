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

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * Implementation of the ValidationService interface that handles data validation and business rule application
 * for the MCA application. It validates application data, document data, and merchant details against predefined
 * schemas and business rules.
 * 
 * This service is responsible for:
 * 1. Validating data against predefined schemas
 * 2. Applying business rules to determine application status
 * 3. Validating document data for completeness and accuracy
 * 4. Ensuring data integrity across the application
 * 5. Reporting validation results with detailed error messages
 */
@Service
public class ValidationServiceImpl implements ValidationService {

    private static final Logger logger = LoggerFactory.getLogger(ValidationServiceImpl.class);
    
    // Minimum confidence threshold for OCR data extraction
    private static final double MIN_CONFIDENCE_THRESHOLD = 0.75;
    
    // Minimum required documents for a complete application
    private static final Map<DocumentType, Integer> REQUIRED_DOCUMENT_COUNTS;
    
    // Document validation schemas
    private final Map<DocumentType, Map<String, Object>> documentValidationSchemas = new ConcurrentHashMap<>();
    
    static {
        // Initialize required document counts
        Map<DocumentType, Integer> requiredCounts = new HashMap<>();
        requiredCounts.put(DocumentType.BANK_STATEMENT, 3); // Last 3 months of bank statements
        requiredCounts.put(DocumentType.TAX_RETURN, 1);     // Most recent tax return
        requiredCounts.put(DocumentType.BUSINESS_LICENSE, 1); // Business license
        requiredCounts.put(DocumentType.ID_VERIFICATION, 1);  // ID verification document
        REQUIRED_DOCUMENT_COUNTS = Collections.unmodifiableMap(requiredCounts);
    }
    
    @Autowired
    private RedisCacheService cacheService;
    
    @Autowired
    private CacheKeyGenerator cacheKeyGenerator;
    
    @Autowired
    private ErrorUtil errorUtil;
    
    /**
     * Initializes the validation service by loading validation schemas and business rules.
     */
    @PostConstruct
    public void init() {
        initializeValidationSchemas();
        logger.info("ValidationService initialized with {} document validation schemas", documentValidationSchemas.size());
    }
    
    /**
     * Initializes document validation schemas for different document types.
     */
    private void initializeValidationSchemas() {
        // Bank Statement schema
        Map<String, Object> bankStatementSchema = new HashMap<>();
        bankStatementSchema.put("accountNumber", Map.of("type", "string", "required", true, "pattern", "^[0-9]{8,17}$"));
        bankStatementSchema.put("routingNumber", Map.of("type", "string", "required", true, "pattern", "^[0-9]{9}$"));
        bankStatementSchema.put("bankName", Map.of("type", "string", "required", true));
        bankStatementSchema.put("accountName", Map.of("type", "string", "required", true));
        bankStatementSchema.put("statementDate", Map.of("type", "date", "required", true));
        bankStatementSchema.put("beginningBalance", Map.of("type", "number", "required", true));
        bankStatementSchema.put("endingBalance", Map.of("type", "number", "required", true));
        bankStatementSchema.put("averageDailyBalance", Map.of("type", "number", "required", true));
        bankStatementSchema.put("totalDeposits", Map.of("type", "number", "required", true));
        bankStatementSchema.put("totalWithdrawals", Map.of("type", "number", "required", true));
        documentValidationSchemas.put(DocumentType.BANK_STATEMENT, bankStatementSchema);
        
        // Tax Return schema
        Map<String, Object> taxReturnSchema = new HashMap<>();
        taxReturnSchema.put("taxYear", Map.of("type", "integer", "required", true));
        taxReturnSchema.put("ein", Map.of("type", "string", "required", true, "pattern", "^[0-9]{2}-[0-9]{7}$"));
        taxReturnSchema.put("businessName", Map.of("type", "string", "required", true));
        taxReturnSchema.put("grossRevenue", Map.of("type", "number", "required", true));
        taxReturnSchema.put("netIncome", Map.of("type", "number", "required", true));
        taxReturnSchema.put("taxLiability", Map.of("type", "number", "required", true));
        documentValidationSchemas.put(DocumentType.TAX_RETURN, taxReturnSchema);
        
        // Business License schema
        Map<String, Object> businessLicenseSchema = new HashMap<>();
        businessLicenseSchema.put("licenseNumber", Map.of("type", "string", "required", true));
        businessLicenseSchema.put("businessName", Map.of("type", "string", "required", true));
        businessLicenseSchema.put("issueDate", Map.of("type", "date", "required", true));
        businessLicenseSchema.put("expirationDate", Map.of("type", "date", "required", true));
        businessLicenseSchema.put("licenseType", Map.of("type", "string", "required", true));
        businessLicenseSchema.put("issuingAuthority", Map.of("type", "string", "required", true));
        documentValidationSchemas.put(DocumentType.BUSINESS_LICENSE, businessLicenseSchema);
        
        // ID Verification schema
        Map<String, Object> idVerificationSchema = new HashMap<>();
        idVerificationSchema.put("idType", Map.of("type", "string", "required", true, "enum", List.of("DRIVERS_LICENSE", "PASSPORT", "STATE_ID")));
        idVerificationSchema.put("idNumber", Map.of("type", "string", "required", true));
        idVerificationSchema.put("fullName", Map.of("type", "string", "required", true));
        idVerificationSchema.put("dateOfBirth", Map.of("type", "date", "required", true));
        idVerificationSchema.put("expirationDate", Map.of("type", "date", "required", true));
        idVerificationSchema.put("issuingAuthority", Map.of("type", "string", "required", true));
        documentValidationSchemas.put(DocumentType.ID_VERIFICATION, idVerificationSchema);
        
        // Invoice schema
        Map<String, Object> invoiceSchema = new HashMap<>();
        invoiceSchema.put("invoiceNumber", Map.of("type", "string", "required", true));
        invoiceSchema.put("invoiceDate", Map.of("type", "date", "required", true));
        invoiceSchema.put("dueDate", Map.of("type", "date", "required", true));
        invoiceSchema.put("customerName", Map.of("type", "string", "required", true));
        invoiceSchema.put("totalAmount", Map.of("type", "number", "required", true));
        invoiceSchema.put("items", Map.of("type", "array", "required", true));
        documentValidationSchemas.put(DocumentType.INVOICE, invoiceSchema);
        
        // Miscellaneous schema (minimal requirements)
        Map<String, Object> miscSchema = new HashMap<>();
        miscSchema.put("documentTitle", Map.of("type", "string", "required", true));
        miscSchema.put("documentDate", Map.of("type", "date", "required", true));
        documentValidationSchemas.put(DocumentType.MISCELLANEOUS, miscSchema);
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult validateApplicationData(ApplicationRequestDTO applicationDTO) {
        logger.debug("Validating application data: {}", applicationDTO);
        
        // Check for cached validation result
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "application", applicationDTO.hashCode());
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for application data");
            return cachedResult;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Validate required fields
        if (applicationDTO.getStatus() == null) {
            errors.put("status", "Application status is required");
        }
        
        // Validate metadata if present
        if (applicationDTO.getMetadata() != null) {
            // Validate metadata structure and content
            if (!isValidJson(applicationDTO.getMetadata())) {
                errors.put("metadata", "Metadata must be a valid JSON object");
            }
        }
        
        // Create validation result
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult validateDocumentData(DocumentRequestDTO documentDTO) {
        logger.debug("Validating document data: {}", documentDTO);
        
        // Check for cached validation result
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "document", documentDTO.hashCode());
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for document data");
            return cachedResult;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Validate required fields
        if (documentDTO.getType() == null) {
            errors.put("type", "Document type is required");
        }
        
        if (documentDTO.getApplicationId() == null) {
            errors.put("applicationId", "Application ID is required");
        }
        
        // Validate metadata if present
        if (documentDTO.getMetadata() != null) {
            // Validate metadata structure and content
            if (!isValidJson(documentDTO.getMetadata())) {
                errors.put("metadata", "Metadata must be a valid JSON object");
            }
        }
        
        // Create validation result
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult validateMerchantDetails(MerchantDetailsRequestDTO merchantDetailsDTO) {
        logger.debug("Validating merchant details: {}", merchantDetailsDTO);
        
        // Check for cached validation result
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "merchant", merchantDetailsDTO.hashCode());
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for merchant details");
            return cachedResult;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Validate required fields
        if (merchantDetailsDTO.getApplicationId() == null) {
            errors.put("applicationId", "Application ID is required");
        }
        
        if (merchantDetailsDTO.getLegalName() == null || merchantDetailsDTO.getLegalName().trim().isEmpty()) {
            errors.put("legalName", "Legal name is required");
        }
        
        if (merchantDetailsDTO.getEin() == null || !isValidEin(merchantDetailsDTO.getEin())) {
            errors.put("ein", "Valid EIN is required (format: XX-XXXXXXX)");
        }
        
        // Validate address if present
        if (merchantDetailsDTO.getAddress() != null) {
            // Validate address structure
            if (merchantDetailsDTO.getAddress().get("street1") == null || 
                merchantDetailsDTO.getAddress().get("city") == null || 
                merchantDetailsDTO.getAddress().get("state") == null || 
                merchantDetailsDTO.getAddress().get("zipCode") == null) {
                errors.put("address", "Address must include street1, city, state, and zipCode");
            } else {
                // Validate zip code format
                String zipCode = (String) merchantDetailsDTO.getAddress().get("zipCode");
                if (!isValidZipCode(zipCode)) {
                    errors.put("address.zipCode", "Invalid zip code format");
                }
            }
        } else {
            errors.put("address", "Address is required");
        }
        
        // Validate industry if present
        if (merchantDetailsDTO.getIndustry() == null || merchantDetailsDTO.getIndustry().trim().isEmpty()) {
            errors.put("industry", "Industry is required");
        }
        
        // Validate revenue if present
        if (merchantDetailsDTO.getRevenue() == null || merchantDetailsDTO.getRevenue() <= 0) {
            errors.put("revenue", "Valid revenue amount is required");
        }
        
        // Create validation result
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult validateApplication(Application application) {
        logger.debug("Validating application entity: {}", application.getId());
        
        // Check for cached validation result
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "application_entity", application.getId());
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for application entity");
            return cachedResult;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Validate required fields
        if (application.getStatus() == null) {
            errors.put("status", "Application status is required");
        }
        
        if (application.getReviewStatus() == null) {
            errors.put("reviewStatus", "Review status is required");
        }
        
        // Validate created and updated timestamps
        if (application.getCreatedAt() == null) {
            errors.put("createdAt", "Created timestamp is required");
        }
        
        if (application.getUpdatedAt() == null) {
            errors.put("updatedAt", "Updated timestamp is required");
        }
        
        // Validate metadata if present
        if (application.getMetadata() != null) {
            // Validate metadata structure and content
            if (!isValidJson(application.getMetadata())) {
                errors.put("metadata", "Metadata must be a valid JSON object");
            }
        }
        
        // Create validation result
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult validateDocument(Document document) {
        logger.debug("Validating document entity: {}", document.getId());
        
        // Check for cached validation result
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "document_entity", document.getId());
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for document entity");
            return cachedResult;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Validate required fields
        if (document.getType() == null) {
            errors.put("type", "Document type is required");
        }
        
        if (document.getApplication() == null) {
            errors.put("application", "Application association is required");
        }
        
        if (document.getStoragePath() == null || document.getStoragePath().trim().isEmpty()) {
            errors.put("storagePath", "Storage path is required");
        }
        
        if (document.getUploadedAt() == null) {
            errors.put("uploadedAt", "Upload timestamp is required");
        }
        
        // Validate metadata if present
        if (document.getMetadata() != null) {
            // Validate metadata structure and content
            if (!isValidJson(document.getMetadata())) {
                errors.put("metadata", "Metadata must be a valid JSON object");
            }
        }
        
        // Create validation result
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult validateMerchant(MerchantDetails merchantDetails) {
        logger.debug("Validating merchant details entity: {}", merchantDetails.getId());
        
        // Check for cached validation result
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "merchant_entity", merchantDetails.getId());
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for merchant details entity");
            return cachedResult;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Validate required fields
        if (merchantDetails.getApplication() == null) {
            errors.put("application", "Application association is required");
        }
        
        if (merchantDetails.getLegalName() == null || merchantDetails.getLegalName().trim().isEmpty()) {
            errors.put("legalName", "Legal name is required");
        }
        
        if (merchantDetails.getEin() == null || !isValidEin(merchantDetails.getEin())) {
            errors.put("ein", "Valid EIN is required (format: XX-XXXXXXX)");
        }
        
        // Validate address if present
        if (merchantDetails.getAddress() == null || merchantDetails.getAddress().isEmpty()) {
            errors.put("address", "Address is required");
        }
        
        // Validate industry if present
        if (merchantDetails.getIndustry() == null || merchantDetails.getIndustry().trim().isEmpty()) {
            errors.put("industry", "Industry is required");
        }
        
        // Validate revenue if present
        if (merchantDetails.getRevenue() == null || merchantDetails.getRevenue() <= 0) {
            errors.put("revenue", "Valid revenue amount is required");
        }
        
        // Create validation result
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult evaluateApplicationCompleteness(Application application) {
        logger.debug("Evaluating application completeness: {}", application.getId());
        
        // Check for cached validation result
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "application_completeness", application.getId());
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for application completeness");
            return cachedResult;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Check if merchant details exist and are valid
        MerchantDetails merchantDetails = application.getMerchantDetails();
        if (merchantDetails == null) {
            errors.put("merchantDetails", "Merchant details are required for a complete application");
        } else {
            ValidationResult merchantValidation = validateMerchant(merchantDetails);
            if (!merchantValidation.isValid()) {
                errors.put("merchantDetailsValidation", "Merchant details validation failed: " + 
                          merchantValidation.getErrors().values().stream().collect(Collectors.joining(", ")));
            }
        }
        
        // Check if required documents exist and are valid
        List<Document> documents = application.getDocuments();
        if (documents == null || documents.isEmpty()) {
            errors.put("documents", "Documents are required for a complete application");
        } else {
            ValidationResult documentsValidation = validateRequiredDocuments(documents);
            if (!documentsValidation.isValid()) {
                errors.put("documentsValidation", "Required documents validation failed: " + 
                          documentsValidation.getErrors().values().stream().collect(Collectors.joining(", ")));
            }
        }
        
        // Check application status
        if (application.getStatus() == ApplicationStatus.NEW || application.getStatus() == ApplicationStatus.PENDING) {
            errors.put("applicationStatus", "Application is still in NEW or PENDING status");
        }
        
        // Create validation result with appropriate severity
        ValidationSeverity severity = errors.isEmpty() ? ValidationSeverity.NONE : ValidationSeverity.WARNING;
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors, severity);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ApplicationStatus determineApplicationStatus(Application application) {
        logger.debug("Determining application status: {}", application.getId());
        
        // Check if application has all required documents
        ValidationResult documentsValidation = validateRequiredDocuments(application.getDocuments());
        
        // Check if merchant details are complete
        MerchantDetails merchantDetails = application.getMerchantDetails();
        boolean hasMerchantDetails = merchantDetails != null;
        
        // Determine status based on completeness
        if (!hasMerchantDetails || !documentsValidation.isValid()) {
            return ApplicationStatus.PENDING;
        }
        
        // Check review status to determine application status
        ReviewStatus reviewStatus = application.getReviewStatus();
        if (reviewStatus == null) {
            return ApplicationStatus.PROCESSING;
        }
        
        switch (reviewStatus) {
            case APPROVED:
                return ApplicationStatus.APPROVED;
            case REJECTED:
                return ApplicationStatus.REJECTED;
            case NEEDS_INFORMATION:
                return ApplicationStatus.PENDING;
            case IN_REVIEW:
                return ApplicationStatus.PROCESSING;
            case NOT_REVIEWED:
            default:
                return ApplicationStatus.PROCESSING;
        }
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ReviewStatus determineReviewStatus(Application application) {
        logger.debug("Determining review status: {}", application.getId());
        
        // Check if application has all required documents
        ValidationResult documentsValidation = validateRequiredDocuments(application.getDocuments());
        
        // Check if merchant details are complete
        MerchantDetails merchantDetails = application.getMerchantDetails();
        boolean hasMerchantDetails = merchantDetails != null;
        
        // If application is incomplete, it needs information
        if (!hasMerchantDetails || !documentsValidation.isValid()) {
            return ReviewStatus.NEEDS_INFORMATION;
        }
        
        // If application is complete but not reviewed, set to IN_REVIEW
        if (application.getReviewStatus() == ReviewStatus.NOT_REVIEWED) {
            return ReviewStatus.IN_REVIEW;
        }
        
        // Otherwise, maintain current review status
        return application.getReviewStatus();
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult validateExtractedData(DocumentType documentType, Map<String, Object> extractedData) {
        logger.debug("Validating extracted data for document type: {}", documentType);
        
        // Generate cache key based on document type and extracted data hash
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "extracted_data", 
                                                      documentType.toString() + extractedData.hashCode());
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for extracted data");
            return cachedResult;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Get validation schema for document type
        Map<String, Object> schema = getDocumentValidationSchema(documentType);
        if (schema == null) {
            errors.put("schema", "No validation schema found for document type: " + documentType);
            return new ValidationResult(false, errors, ValidationSeverity.ERROR);
        }
        
        // Validate extracted data against schema
        for (Map.Entry<String, Object> schemaEntry : schema.entrySet()) {
            String fieldName = schemaEntry.getKey();
            Map<String, Object> fieldSchema = (Map<String, Object>) schemaEntry.getValue();
            
            // Check if field is required
            boolean required = (boolean) fieldSchema.getOrDefault("required", false);
            if (required && (!extractedData.containsKey(fieldName) || extractedData.get(fieldName) == null)) {
                errors.put(fieldName, "Required field is missing");
                continue;
            }
            
            // Skip validation if field is not present and not required
            if (!extractedData.containsKey(fieldName) || extractedData.get(fieldName) == null) {
                continue;
            }
            
            // Validate field based on type
            String fieldType = (String) fieldSchema.get("type");
            Object fieldValue = extractedData.get(fieldName);
            
            switch (fieldType) {
                case "string":
                    if (!(fieldValue instanceof String)) {
                        errors.put(fieldName, "Field must be a string");
                    } else {
                        // Check pattern if specified
                        if (fieldSchema.containsKey("pattern")) {
                            String pattern = (String) fieldSchema.get("pattern");
                            if (!((String) fieldValue).matches(pattern)) {
                                errors.put(fieldName, "Field does not match required pattern");
                            }
                        }
                        
                        // Check enum if specified
                        if (fieldSchema.containsKey("enum")) {
                            List<String> enumValues = (List<String>) fieldSchema.get("enum");
                            if (!enumValues.contains(fieldValue)) {
                                errors.put(fieldName, "Field value must be one of: " + String.join(", ", enumValues));
                            }
                        }
                    }
                    break;
                case "number":
                    if (!(fieldValue instanceof Number)) {
                        errors.put(fieldName, "Field must be a number");
                    }
                    break;
                case "integer":
                    if (!(fieldValue instanceof Integer) && !(fieldValue instanceof Long)) {
                        errors.put(fieldName, "Field must be an integer");
                    }
                    break;
                case "date":
                    if (!(fieldValue instanceof String) || !isValidDate((String) fieldValue)) {
                        errors.put(fieldName, "Field must be a valid date");
                    }
                    break;
                case "array":
                    if (!(fieldValue instanceof List)) {
                        errors.put(fieldName, "Field must be an array");
                    }
                    break;
                default:
                    errors.put(fieldName, "Unknown field type: " + fieldType);
            }
        }
        
        // Create validation result with appropriate severity
        ValidationSeverity severity = errors.isEmpty() ? ValidationSeverity.NONE : ValidationSeverity.ERROR;
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors, severity);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult validateExtractedDataWithConfidence(DocumentType documentType, 
                                                             Map<String, Object> extractedData,
                                                             Map<String, Double> confidenceScores) {
        logger.debug("Validating extracted data with confidence scores for document type: {}", documentType);
        
        // Generate cache key based on document type, extracted data hash, and confidence scores hash
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "extracted_data_confidence", 
                                                      documentType.toString() + extractedData.hashCode() + confidenceScores.hashCode());
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for extracted data with confidence");
            return cachedResult;
        }
        
        // First validate the extracted data against the schema
        ValidationResult schemaValidation = validateExtractedData(documentType, extractedData);
        
        // If schema validation failed, return the result
        if (!schemaValidation.isValid()) {
            return schemaValidation;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Check confidence scores for each field
        for (Map.Entry<String, Object> entry : extractedData.entrySet()) {
            String fieldName = entry.getKey();
            
            // Skip if no confidence score for this field
            if (!confidenceScores.containsKey(fieldName)) {
                continue;
            }
            
            Double confidence = confidenceScores.get(fieldName);
            if (confidence < MIN_CONFIDENCE_THRESHOLD) {
                errors.put(fieldName, "Low confidence score: " + confidence + 
                          " (below threshold of " + MIN_CONFIDENCE_THRESHOLD + ")");
            }
        }
        
        // Determine severity based on confidence scores
        ValidationSeverity severity;
        if (errors.isEmpty()) {
            severity = ValidationSeverity.NONE;
        } else {
            // If any field has very low confidence, mark as ERROR, otherwise WARNING
            boolean hasVeryLowConfidence = confidenceScores.values().stream()
                .anyMatch(confidence -> confidence < MIN_CONFIDENCE_THRESHOLD / 2);
            severity = hasVeryLowConfidence ? ValidationSeverity.ERROR : ValidationSeverity.WARNING;
        }
        
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors, severity);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult validateRequiredDocuments(List<Document> documents) {
        logger.debug("Validating required documents: {}", documents != null ? documents.size() : 0);
        
        // Generate cache key based on document IDs
        String documentIds = documents != null ? 
                           documents.stream().map(doc -> doc.getId().toString()).collect(Collectors.joining("-")) : 
                           "empty";
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "required_documents", documentIds);
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for required documents");
            return cachedResult;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Check if documents list is null or empty
        if (documents == null || documents.isEmpty()) {
            errors.put("documents", "No documents provided");
            return new ValidationResult(false, errors, ValidationSeverity.ERROR);
        }
        
        // Count documents by type
        Map<DocumentType, Integer> documentCounts = new HashMap<>();
        for (Document document : documents) {
            DocumentType type = document.getType();
            documentCounts.put(type, documentCounts.getOrDefault(type, 0) + 1);
        }
        
        // Check if all required document types are present with sufficient counts
        for (Map.Entry<DocumentType, Integer> entry : REQUIRED_DOCUMENT_COUNTS.entrySet()) {
            DocumentType requiredType = entry.getKey();
            Integer requiredCount = entry.getValue();
            Integer actualCount = documentCounts.getOrDefault(requiredType, 0);
            
            if (actualCount < requiredCount) {
                errors.put(requiredType.toString(), "Required " + requiredCount + " document(s) of type " + 
                          requiredType + ", but found only " + actualCount);
            }
        }
        
        // Determine severity based on missing documents
        ValidationSeverity severity;
        if (errors.isEmpty()) {
            severity = ValidationSeverity.NONE;
        } else {
            // If all required document types are missing, mark as ERROR, otherwise WARNING
            boolean allMissing = REQUIRED_DOCUMENT_COUNTS.keySet().stream()
                .noneMatch(documentCounts::containsKey);
            severity = allMissing ? ValidationSeverity.ERROR : ValidationSeverity.WARNING;
        }
        
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors, severity);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult validateBusinessRules(Application application, 
                                               MerchantDetails merchantDetails,
                                               List<Document> documents) {
        logger.debug("Validating business rules for application: {}", application.getId());
        
        // Generate cache key based on application ID, merchant ID, and document IDs
        String documentIds = documents != null ? 
                           documents.stream().map(doc -> doc.getId().toString()).collect(Collectors.joining("-")) : 
                           "empty";
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "business_rules", 
                                                      application.getId() + "-" + 
                                                      (merchantDetails != null ? merchantDetails.getId() : "null") + "-" + 
                                                      documentIds);
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for business rules");
            return cachedResult;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Validate application completeness
        ValidationResult completenessValidation = evaluateApplicationCompleteness(application);
        if (!completenessValidation.isValid()) {
            errors.put("completeness", "Application is incomplete: " + 
                      completenessValidation.getErrors().values().stream().collect(Collectors.joining(", ")));
        }
        
        // Validate merchant details
        if (merchantDetails == null) {
            errors.put("merchantDetails", "Merchant details are required");
        } else {
            // Check minimum revenue requirement
            if (merchantDetails.getRevenue() < 100000) { // $100,000 minimum revenue
                errors.put("revenue", "Merchant revenue must be at least $100,000");
            }
            
            // Check business age requirement (based on metadata)
            if (merchantDetails.getMetadata() != null && merchantDetails.getMetadata().containsKey("businessStartDate")) {
                String businessStartDate = (String) merchantDetails.getMetadata().get("businessStartDate");
                if (isValidDate(businessStartDate) && !isBusinessOlderThanOneYear(businessStartDate)) {
                    errors.put("businessAge", "Business must be at least one year old");
                }
            } else {
                errors.put("businessStartDate", "Business start date is required in merchant metadata");
            }
        }
        
        // Validate bank statements
        List<Document> bankStatements = documents.stream()
            .filter(doc -> doc.getType() == DocumentType.BANK_STATEMENT)
            .collect(Collectors.toList());
        
        if (bankStatements.size() < 3) {
            errors.put("bankStatements", "At least 3 months of bank statements are required");
        } else {
            // Check for consecutive months in bank statements
            if (!hasConsecutiveMonthsOfBankStatements(bankStatements)) {
                errors.put("bankStatementMonths", "Bank statements must cover consecutive months");
            }
            
            // Check average daily balance
            double avgDailyBalance = calculateAverageDailyBalance(bankStatements);
            if (avgDailyBalance < 5000) { // $5,000 minimum average daily balance
                errors.put("avgDailyBalance", "Average daily balance must be at least $5,000");
            }
        }
        
        // Validate tax return
        List<Document> taxReturns = documents.stream()
            .filter(doc -> doc.getType() == DocumentType.TAX_RETURN)
            .collect(Collectors.toList());
        
        if (taxReturns.isEmpty()) {
            errors.put("taxReturn", "Tax return is required");
        } else {
            // Check if tax return is for the most recent tax year
            if (!isRecentTaxReturn(taxReturns.get(0))) {
                errors.put("taxReturnYear", "Tax return must be for the most recent tax year");
            }
        }
        
        // Determine severity based on rule violations
        ValidationSeverity severity;
        if (errors.isEmpty()) {
            severity = ValidationSeverity.NONE;
        } else {
            // If critical rules are violated, mark as ERROR, otherwise WARNING
            boolean hasCriticalViolations = errors.containsKey("merchantDetails") || 
                                          errors.containsKey("bankStatements") || 
                                          errors.containsKey("taxReturn");
            severity = hasCriticalViolations ? ValidationSeverity.ERROR : ValidationSeverity.WARNING;
        }
        
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors, severity);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult validateApprovalRequirements(Application application,
                                                      MerchantDetails merchantDetails,
                                                      List<Document> documents) {
        logger.debug("Validating approval requirements for application: {}", application.getId());
        
        // Generate cache key based on application ID, merchant ID, and document IDs
        String documentIds = documents != null ? 
                           documents.stream().map(doc -> doc.getId().toString()).collect(Collectors.joining("-")) : 
                           "empty";
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "approval_requirements", 
                                                      application.getId() + "-" + 
                                                      (merchantDetails != null ? merchantDetails.getId() : "null") + "-" + 
                                                      documentIds);
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for approval requirements");
            return cachedResult;
        }
        
        // First validate business rules
        ValidationResult businessRulesValidation = validateBusinessRules(application, merchantDetails, documents);
        
        // If business rules validation failed, application cannot be approved
        if (!businessRulesValidation.isValid()) {
            return businessRulesValidation;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Check additional approval requirements
        
        // Check revenue to advance ratio
        if (merchantDetails != null && application.getMetadata() != null) {
            if (application.getMetadata().containsKey("requestedAmount")) {
                double requestedAmount = Double.parseDouble(application.getMetadata().get("requestedAmount").toString());
                double revenue = merchantDetails.getRevenue();
                
                // Requested amount should not exceed 20% of annual revenue
                if (requestedAmount > revenue * 0.2) {
                    errors.put("requestedAmount", "Requested amount exceeds 20% of annual revenue");
                }
            } else {
                errors.put("requestedAmount", "Requested amount is required for approval");
            }
        }
        
        // Check bank statement deposit consistency
        List<Document> bankStatements = documents.stream()
            .filter(doc -> doc.getType() == DocumentType.BANK_STATEMENT)
            .collect(Collectors.toList());
        
        if (!bankStatements.isEmpty()) {
            // Check for consistent deposit patterns
            if (!hasConsistentDepositPattern(bankStatements)) {
                errors.put("depositPattern", "Bank statements must show consistent deposit patterns");
            }
            
            // Check for sufficient deposit volume
            if (!hasSufficientDepositVolume(bankStatements)) {
                errors.put("depositVolume", "Bank statements must show sufficient deposit volume");
            }
        }
        
        // Check business license validity
        List<Document> businessLicenses = documents.stream()
            .filter(doc -> doc.getType() == DocumentType.BUSINESS_LICENSE)
            .collect(Collectors.toList());
        
        if (!businessLicenses.isEmpty()) {
            if (!isBusinessLicenseValid(businessLicenses.get(0))) {
                errors.put("businessLicense", "Business license must be valid and not expired");
            }
        }
        
        // Determine severity based on approval requirement violations
        ValidationSeverity severity;
        if (errors.isEmpty()) {
            severity = ValidationSeverity.NONE;
        } else {
            // If critical approval requirements are violated, mark as ERROR, otherwise WARNING
            boolean hasCriticalViolations = errors.containsKey("requestedAmount") || 
                                          errors.containsKey("depositPattern") || 
                                          errors.containsKey("businessLicense");
            severity = hasCriticalViolations ? ValidationSeverity.ERROR : ValidationSeverity.WARNING;
        }
        
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors, severity);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult validateApplicationDataConsistency(Application application,
                                                            Map<DocumentType, Map<String, Object>> extractedDataMap) {
        logger.debug("Validating application data consistency: {}", application.getId());
        
        // Generate cache key based on application ID and extracted data map hash
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "application_data_consistency", 
                                                      application.getId() + "-" + extractedDataMap.hashCode());
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for application data consistency");
            return cachedResult;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Check if application metadata is consistent with extracted document data
        if (application.getMetadata() != null && !extractedDataMap.isEmpty()) {
            // Check business name consistency
            if (application.getMetadata().containsKey("businessName")) {
                String appBusinessName = application.getMetadata().get("businessName").toString();
                
                // Check against business license
                if (extractedDataMap.containsKey(DocumentType.BUSINESS_LICENSE)) {
                    Map<String, Object> licenseData = extractedDataMap.get(DocumentType.BUSINESS_LICENSE);
                    if (licenseData.containsKey("businessName")) {
                        String licenseBusinessName = licenseData.get("businessName").toString();
                        if (!isNameMatch(appBusinessName, licenseBusinessName)) {
                            errors.put("businessName", "Business name in application (" + appBusinessName + 
                                      ") does not match business license (" + licenseBusinessName + ")");
                        }
                    }
                }
                
                // Check against tax return
                if (extractedDataMap.containsKey(DocumentType.TAX_RETURN)) {
                    Map<String, Object> taxData = extractedDataMap.get(DocumentType.TAX_RETURN);
                    if (taxData.containsKey("businessName")) {
                        String taxBusinessName = taxData.get("businessName").toString();
                        if (!isNameMatch(appBusinessName, taxBusinessName)) {
                            errors.put("businessNameTax", "Business name in application (" + appBusinessName + 
                                      ") does not match tax return (" + taxBusinessName + ")");
                        }
                    }
                }
            }
            
            // Check requested amount consistency
            if (application.getMetadata().containsKey("requestedAmount")) {
                double requestedAmount = Double.parseDouble(application.getMetadata().get("requestedAmount").toString());
                
                // Check against bank statements for reasonableness
                if (extractedDataMap.containsKey(DocumentType.BANK_STATEMENT)) {
                    Map<String, Object> bankData = extractedDataMap.get(DocumentType.BANK_STATEMENT);
                    if (bankData.containsKey("averageDailyBalance")) {
                        double avgBalance = Double.parseDouble(bankData.get("averageDailyBalance").toString());
                        if (requestedAmount > avgBalance * 10) { // Requested amount should not exceed 10x avg balance
                            errors.put("requestedAmountBalance", "Requested amount (" + requestedAmount + 
                                      ") exceeds 10x average daily balance (" + avgBalance + ")");
                        }
                    }
                }
            }
        }
        
        // Determine severity based on consistency violations
        ValidationSeverity severity;
        if (errors.isEmpty()) {
            severity = ValidationSeverity.NONE;
        } else {
            // If critical consistency issues are found, mark as ERROR, otherwise WARNING
            severity = ValidationSeverity.WARNING;
        }
        
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors, severity);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult validateDataConsistency(MerchantDetails merchantDetails,
                                                 Map<DocumentType, Map<String, Object>> extractedDataMap) {
        logger.debug("Validating merchant data consistency: {}", merchantDetails.getId());
        
        // Generate cache key based on merchant ID and extracted data map hash
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "merchant_data_consistency", 
                                                      merchantDetails.getId() + "-" + extractedDataMap.hashCode());
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for merchant data consistency");
            return cachedResult;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Check if merchant details are consistent with extracted document data
        if (!extractedDataMap.isEmpty()) {
            // Check business name consistency
            String merchantLegalName = merchantDetails.getLegalName();
            String merchantDbaName = merchantDetails.getDbaName();
            
            // Check against business license
            if (extractedDataMap.containsKey(DocumentType.BUSINESS_LICENSE)) {
                Map<String, Object> licenseData = extractedDataMap.get(DocumentType.BUSINESS_LICENSE);
                if (licenseData.containsKey("businessName")) {
                    String licenseBusinessName = licenseData.get("businessName").toString();
                    if (!isNameMatch(merchantLegalName, licenseBusinessName) && 
                        (merchantDbaName == null || !isNameMatch(merchantDbaName, licenseBusinessName))) {
                        errors.put("businessName", "Merchant name (" + merchantLegalName + 
                                  (merchantDbaName != null ? " / " + merchantDbaName : "") + 
                                  ") does not match business license (" + licenseBusinessName + ")");
                    }
                }
            }
            
            // Check EIN consistency
            String merchantEin = merchantDetails.getEin();
            
            // Check against tax return
            if (extractedDataMap.containsKey(DocumentType.TAX_RETURN)) {
                Map<String, Object> taxData = extractedDataMap.get(DocumentType.TAX_RETURN);
                if (taxData.containsKey("ein")) {
                    String taxEin = taxData.get("ein").toString();
                    if (!merchantEin.equals(taxEin)) {
                        errors.put("ein", "Merchant EIN (" + merchantEin + 
                                  ") does not match tax return EIN (" + taxEin + ")");
                    }
                }
            }
            
            // Check revenue consistency
            Double merchantRevenue = merchantDetails.getRevenue();
            
            // Check against tax return
            if (extractedDataMap.containsKey(DocumentType.TAX_RETURN)) {
                Map<String, Object> taxData = extractedDataMap.get(DocumentType.TAX_RETURN);
                if (taxData.containsKey("grossRevenue")) {
                    double taxRevenue = Double.parseDouble(taxData.get("grossRevenue").toString());
                    // Allow for 10% variance
                    double variance = Math.abs(merchantRevenue - taxRevenue) / taxRevenue;
                    if (variance > 0.1) {
                        errors.put("revenue", "Merchant revenue (" + merchantRevenue + 
                                  ") differs significantly from tax return revenue (" + taxRevenue + ")");
                    }
                }
            }
        }
        
        // Determine severity based on consistency violations
        ValidationSeverity severity;
        if (errors.isEmpty()) {
            severity = ValidationSeverity.NONE;
        } else {
            // If critical consistency issues are found, mark as ERROR, otherwise WARNING
            boolean hasCriticalViolations = errors.containsKey("ein");
            severity = hasCriticalViolations ? ValidationSeverity.ERROR : ValidationSeverity.WARNING;
        }
        
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors, severity);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult validateDataQuality(Map<DocumentType, Map<String, Object>> extractedDataMap,
                                              Map<DocumentType, Map<String, Double>> confidenceScoresMap) {
        logger.debug("Validating data quality for {} document types", extractedDataMap.size());
        
        // Generate cache key based on extracted data map hash and confidence scores map hash
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "data_quality", 
                                                      extractedDataMap.hashCode() + "-" + confidenceScoresMap.hashCode());
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for data quality");
            return cachedResult;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Check data quality for each document type
        for (Map.Entry<DocumentType, Map<String, Object>> entry : extractedDataMap.entrySet()) {
            DocumentType documentType = entry.getKey();
            Map<String, Object> extractedData = entry.getValue();
            
            // Skip if no confidence scores for this document type
            if (!confidenceScoresMap.containsKey(documentType)) {
                continue;
            }
            
            Map<String, Double> confidenceScores = confidenceScoresMap.get(documentType);
            
            // Validate extracted data with confidence scores
            ValidationResult validation = validateExtractedDataWithConfidence(documentType, extractedData, confidenceScores);
            
            // Add errors if validation failed
            if (!validation.isValid()) {
                for (Map.Entry<String, String> errorEntry : validation.getErrors().entrySet()) {
                    errors.put(documentType + "." + errorEntry.getKey(), errorEntry.getValue());
                }
            }
            
            // Check for missing key fields based on document type
            Map<String, Object> schema = getDocumentValidationSchema(documentType);
            if (schema != null) {
                for (Map.Entry<String, Object> schemaEntry : schema.entrySet()) {
                    String fieldName = schemaEntry.getKey();
                    Map<String, Object> fieldSchema = (Map<String, Object>) schemaEntry.getValue();
                    
                    // Check if field is required but missing or has low confidence
                    boolean required = (boolean) fieldSchema.getOrDefault("required", false);
                    if (required) {
                        if (!extractedData.containsKey(fieldName) || extractedData.get(fieldName) == null) {
                            errors.put(documentType + "." + fieldName + ".missing", "Required field is missing");
                        } else if (confidenceScores.containsKey(fieldName) && 
                                 confidenceScores.get(fieldName) < MIN_CONFIDENCE_THRESHOLD) {
                            errors.put(documentType + "." + fieldName + ".lowConfidence", 
                                     "Low confidence for required field: " + confidenceScores.get(fieldName));
                        }
                    }
                }
            }
        }
        
        // Determine severity based on data quality issues
        ValidationSeverity severity;
        if (errors.isEmpty()) {
            severity = ValidationSeverity.NONE;
        } else {
            // Count critical fields with issues
            long criticalFieldIssues = errors.keySet().stream()
                .filter(key -> key.contains("ein") || key.contains("businessName") || 
                              key.contains("accountNumber") || key.contains("licenseNumber"))
                .count();
            
            severity = criticalFieldIssues > 0 ? ValidationSeverity.ERROR : ValidationSeverity.WARNING;
        }
        
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors, severity);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public ValidationResult validateDocumentClassification(Document document, Map<String, Object> extractedData) {
        logger.debug("Validating document classification: {}", document.getId());
        
        // Generate cache key based on document ID and extracted data hash
        String cacheKey = cacheKeyGenerator.generateKey(CacheConstants.VALIDATION_CACHE, "document_classification", 
                                                      document.getId() + "-" + extractedData.hashCode());
        ValidationResult cachedResult = cacheService.get(cacheKey, ValidationResult.class);
        if (cachedResult != null) {
            logger.debug("Using cached validation result for document classification");
            return cachedResult;
        }
        
        Map<String, String> errors = new HashMap<>();
        
        // Get validation schema for document type
        DocumentType documentType = document.getType();
        Map<String, Object> schema = getDocumentValidationSchema(documentType);
        
        if (schema == null) {
            errors.put("schema", "No validation schema found for document type: " + documentType);
            return new ValidationResult(false, errors, ValidationSeverity.ERROR);
        }
        
        // Count required fields present in extracted data
        int requiredFieldsPresent = 0;
        int totalRequiredFields = 0;
        
        for (Map.Entry<String, Object> schemaEntry : schema.entrySet()) {
            String fieldName = schemaEntry.getKey();
            Map<String, Object> fieldSchema = (Map<String, Object>) schemaEntry.getValue();
            
            // Check if field is required
            boolean required = (boolean) fieldSchema.getOrDefault("required", false);
            if (required) {
                totalRequiredFields++;
                if (extractedData.containsKey(fieldName) && extractedData.get(fieldName) != null) {
                    requiredFieldsPresent++;
                }
            }
        }
        
        // Calculate percentage of required fields present
        double percentPresent = totalRequiredFields > 0 ? 
                              (double) requiredFieldsPresent / totalRequiredFields * 100 : 
                              0;
        
        // If less than 70% of required fields are present, document may be misclassified
        if (percentPresent < 70) {
            errors.put("classification", "Document may be misclassified as " + documentType + 
                      ". Only " + percentPresent + "% of required fields are present.");
            
            // Try to suggest correct document type
            DocumentType suggestedType = suggestDocumentType(extractedData);
            if (suggestedType != null && suggestedType != documentType) {
                errors.put("suggestedType", "Document might be a " + suggestedType + " instead.");
            }
        }
        
        // Determine severity based on classification confidence
        ValidationSeverity severity;
        if (errors.isEmpty()) {
            severity = ValidationSeverity.NONE;
        } else {
            // If very few required fields are present, mark as ERROR, otherwise WARNING
            severity = percentPresent < 50 ? ValidationSeverity.ERROR : ValidationSeverity.WARNING;
        }
        
        ValidationResult result = new ValidationResult(errors.isEmpty(), errors, severity);
        
        // Cache validation result
        cacheService.put(cacheKey, result, CacheConstants.VALIDATION_RESULT_TTL);
        
        return result;
    }

    /**
     * {@inheritDoc}
     */
    @Override
    public Map<String, Object> getDocumentValidationSchema(DocumentType documentType) {
        return documentValidationSchemas.get(documentType);
    }
    
    /**
     * Checks if a string is a valid JSON object.
     *
     * @param json The string to check
     * @return true if the string is a valid JSON object, false otherwise
     */
    private boolean isValidJson(String json) {
        if (json == null || json.trim().isEmpty()) {
            return false;
        }
        
        try {
            // Simple check for JSON object format
            return json.trim().startsWith("{") && json.trim().endsWith("}");
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * Checks if a string is a valid EIN (Employer Identification Number).
     *
     * @param ein The string to check
     * @return true if the string is a valid EIN, false otherwise
     */
    private boolean isValidEin(String ein) {
        if (ein == null || ein.trim().isEmpty()) {
            return false;
        }
        
        // EIN format: XX-XXXXXXX
        return ein.matches("^[0-9]{2}-[0-9]{7}$");
    }
    
    /**
     * Checks if a string is a valid zip code.
     *
     * @param zipCode The string to check
     * @return true if the string is a valid zip code, false otherwise
     */
    private boolean isValidZipCode(String zipCode) {
        if (zipCode == null || zipCode.trim().isEmpty()) {
            return false;
        }
        
        // Zip code formats: XXXXX or XXXXX-XXXX
        return zipCode.matches("^[0-9]{5}(?:-[0-9]{4})?$");
    }
    
    /**
     * Checks if a string is a valid date.
     *
     * @param date The string to check
     * @return true if the string is a valid date, false otherwise
     */
    private boolean isValidDate(String date) {
        if (date == null || date.trim().isEmpty()) {
            return false;
        }
        
        // Simple date format check: YYYY-MM-DD
        return date.matches("^\\d{4}-\\d{2}-\\d{2}$");
    }
    
    /**
     * Checks if a business is older than one year based on its start date.
     *
     * @param startDate The business start date in YYYY-MM-DD format
     * @return true if the business is older than one year, false otherwise
     */
    private boolean isBusinessOlderThanOneYear(String startDate) {
        if (!isValidDate(startDate)) {
            return false;
        }
        
        try {
            // Parse start date
            int year = Integer.parseInt(startDate.substring(0, 4));
            int month = Integer.parseInt(startDate.substring(5, 7));
            int day = Integer.parseInt(startDate.substring(8, 10));
            
            // Get current date
            java.time.LocalDate currentDate = java.time.LocalDate.now();
            java.time.LocalDate businessStartDate = java.time.LocalDate.of(year, month, day);
            
            // Check if business is older than one year
            return businessStartDate.plusYears(1).isBefore(currentDate) || 
                   businessStartDate.plusYears(1).isEqual(currentDate);
        } catch (Exception e) {
            logger.error("Error checking business age: {}", e.getMessage());
            return false;
        }
    }
    
    /**
     * Checks if bank statements cover consecutive months.
     *
     * @param bankStatements List of bank statement documents
     * @return true if bank statements cover consecutive months, false otherwise
     */
    private boolean hasConsecutiveMonthsOfBankStatements(List<Document> bankStatements) {
        if (bankStatements == null || bankStatements.size() < 2) {
            return false;
        }
        
        // Extract statement dates from metadata
        List<java.time.YearMonth> statementMonths = new java.util.ArrayList<>();
        
        for (Document statement : bankStatements) {
            if (statement.getMetadata() != null && statement.getMetadata().contains("statementDate")) {
                String dateStr = statement.getMetadata().get("statementDate").toString();
                if (isValidDate(dateStr)) {
                    try {
                        int year = Integer.parseInt(dateStr.substring(0, 4));
                        int month = Integer.parseInt(dateStr.substring(5, 7));
                        statementMonths.add(java.time.YearMonth.of(year, month));
                    } catch (Exception e) {
                        logger.error("Error parsing statement date: {}", e.getMessage());
                    }
                }
            }
        }
        
        // Sort months
        Collections.sort(statementMonths);
        
        // Check for consecutive months
        for (int i = 1; i < statementMonths.size(); i++) {
            java.time.YearMonth current = statementMonths.get(i);
            java.time.YearMonth previous = statementMonths.get(i - 1);
            
            if (!current.equals(previous.plusMonths(1))) {
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * Calculates the average daily balance from bank statements.
     *
     * @param bankStatements List of bank statement documents
     * @return The average daily balance across all statements
     */
    private double calculateAverageDailyBalance(List<Document> bankStatements) {
        if (bankStatements == null || bankStatements.isEmpty()) {
            return 0.0;
        }
        
        double totalBalance = 0.0;
        int count = 0;
        
        for (Document statement : bankStatements) {
            if (statement.getMetadata() != null && statement.getMetadata().contains("averageDailyBalance")) {
                try {
                    double balance = Double.parseDouble(statement.getMetadata().get("averageDailyBalance").toString());
                    totalBalance += balance;
                    count++;
                } catch (Exception e) {
                    logger.error("Error parsing average daily balance: {}", e.getMessage());
                }
            }
        }
        
        return count > 0 ? totalBalance / count : 0.0;
    }
    
    /**
     * Checks if a tax return is for the most recent tax year.
     *
     * @param taxReturn The tax return document
     * @return true if the tax return is for the most recent tax year, false otherwise
     */
    private boolean isRecentTaxReturn(Document taxReturn) {
        if (taxReturn == null || taxReturn.getMetadata() == null || !taxReturn.getMetadata().contains("taxYear")) {
            return false;
        }
        
        try {
            int taxYear = Integer.parseInt(taxReturn.getMetadata().get("taxYear").toString());
            int currentYear = java.time.LocalDate.now().getYear();
            
            // Tax returns for the previous year are typically filed by April 15 of the current year
            // After April 15, the most recent tax year should be the previous year
            // Before April 15, the most recent tax year should be two years ago
            java.time.LocalDate taxDeadline = java.time.LocalDate.of(currentYear, 4, 15);
            int mostRecentTaxYear = java.time.LocalDate.now().isBefore(taxDeadline) ? 
                                  currentYear - 2 : currentYear - 1;
            
            return taxYear >= mostRecentTaxYear;
        } catch (Exception e) {
            logger.error("Error checking tax return year: {}", e.getMessage());
            return false;
        }
    }
    
    /**
     * Checks if a business license is valid and not expired.
     *
     * @param businessLicense The business license document
     * @return true if the business license is valid and not expired, false otherwise
     */
    private boolean isBusinessLicenseValid(Document businessLicense) {
        if (businessLicense == null || businessLicense.getMetadata() == null || 
            !businessLicense.getMetadata().contains("expirationDate")) {
            return false;
        }
        
        try {
            String expirationDateStr = businessLicense.getMetadata().get("expirationDate").toString();
            if (!isValidDate(expirationDateStr)) {
                return false;
            }
            
            // Parse expiration date
            int year = Integer.parseInt(expirationDateStr.substring(0, 4));
            int month = Integer.parseInt(expirationDateStr.substring(5, 7));
            int day = Integer.parseInt(expirationDateStr.substring(8, 10));
            
            // Check if license is expired
            java.time.LocalDate expirationDate = java.time.LocalDate.of(year, month, day);
            return expirationDate.isAfter(java.time.LocalDate.now());
        } catch (Exception e) {
            logger.error("Error checking business license validity: {}", e.getMessage());
            return false;
        }
    }
    
    /**
     * Checks if bank statements show consistent deposit patterns.
     *
     * @param bankStatements List of bank statement documents
     * @return true if bank statements show consistent deposit patterns, false otherwise
     */
    private boolean hasConsistentDepositPattern(List<Document> bankStatements) {
        if (bankStatements == null || bankStatements.size() < 2) {
            return false;
        }
        
        // Extract total deposits from metadata
        List<Double> deposits = new java.util.ArrayList<>();
        
        for (Document statement : bankStatements) {
            if (statement.getMetadata() != null && statement.getMetadata().contains("totalDeposits")) {
                try {
                    double deposit = Double.parseDouble(statement.getMetadata().get("totalDeposits").toString());
                    deposits.add(deposit);
                } catch (Exception e) {
                    logger.error("Error parsing total deposits: {}", e.getMessage());
                }
            }
        }
        
        if (deposits.size() < 2) {
            return false;
        }
        
        // Calculate average deposit
        double avgDeposit = deposits.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);
        
        // Check if any deposit varies by more than 30% from the average
        for (Double deposit : deposits) {
            double variance = Math.abs(deposit - avgDeposit) / avgDeposit;
            if (variance > 0.3) {
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * Checks if bank statements show sufficient deposit volume.
     *
     * @param bankStatements List of bank statement documents
     * @return true if bank statements show sufficient deposit volume, false otherwise
     */
    private boolean hasSufficientDepositVolume(List<Document> bankStatements) {
        if (bankStatements == null || bankStatements.isEmpty()) {
            return false;
        }
        
        // Extract total deposits from metadata
        double totalDeposits = 0.0;
        int count = 0;
        
        for (Document statement : bankStatements) {
            if (statement.getMetadata() != null && statement.getMetadata().contains("totalDeposits")) {
                try {
                    double deposit = Double.parseDouble(statement.getMetadata().get("totalDeposits").toString());
                    totalDeposits += deposit;
                    count++;
                } catch (Exception e) {
                    logger.error("Error parsing total deposits: {}", e.getMessage());
                }
            }
        }
        
        if (count == 0) {
            return false;
        }
        
        // Calculate average monthly deposits
        double avgMonthlyDeposits = totalDeposits / count;
        
        // Minimum required average monthly deposits: $10,000
        return avgMonthlyDeposits >= 10000;
    }
    
    /**
     * Checks if two business names match, allowing for minor variations.
     *
     * @param name1 The first business name
     * @param name2 The second business name
     * @return true if the names match (allowing for minor variations), false otherwise
     */
    private boolean isNameMatch(String name1, String name2) {
        if (name1 == null || name2 == null) {
            return false;
        }
        
        // Normalize names for comparison
        String normalized1 = normalizeBusinessName(name1);
        String normalized2 = normalizeBusinessName(name2);
        
        // Check for exact match after normalization
        if (normalized1.equals(normalized2)) {
            return true;
        }
        
        // Check for similarity using Levenshtein distance
        int distance = levenshteinDistance(normalized1, normalized2);
        int maxLength = Math.max(normalized1.length(), normalized2.length());
        
        // Allow for some variation based on name length
        double similarity = 1.0 - ((double) distance / maxLength);
        return similarity >= 0.8; // 80% similarity threshold
    }
    
    /**
     * Normalizes a business name for comparison by removing common suffixes,
     * converting to lowercase, and removing non-alphanumeric characters.
     *
     * @param name The business name to normalize
     * @return The normalized business name
     */
    private String normalizeBusinessName(String name) {
        if (name == null) {
            return "";
        }
        
        // Convert to lowercase
        String normalized = name.toLowerCase();
        
        // Remove common business suffixes
        String[] suffixes = {"inc", "incorporated", "llc", "ltd", "limited", "corp", "corporation"};
        for (String suffix : suffixes) {
            normalized = normalized.replaceAll("\\b" + suffix + "\\b", "");
            normalized = normalized.replaceAll("\\b" + suffix + "\\.", "");
        }
        
        // Remove non-alphanumeric characters except spaces
        normalized = normalized.replaceAll("[^a-z0-9\\s]", "");
        
        // Replace multiple spaces with a single space
        normalized = normalized.replaceAll("\\s+", " ");
        
        // Trim leading and trailing spaces
        return normalized.trim();
    }
    
    /**
     * Calculates the Levenshtein distance between two strings.
     *
     * @param s1 The first string
     * @param s2 The second string
     * @return The Levenshtein distance between the two strings
     */
    private int levenshteinDistance(String s1, String s2) {
        int[][] dp = new int[s1.length() + 1][s2.length() + 1];
        
        for (int i = 0; i <= s1.length(); i++) {
            dp[i][0] = i;
        }
        
        for (int j = 0; j <= s2.length(); j++) {
            dp[0][j] = j;
        }
        
        for (int i = 1; i <= s1.length(); i++) {
            for (int j = 1; j <= s2.length(); j++) {
                int cost = (s1.charAt(i - 1) == s2.charAt(j - 1)) ? 0 : 1;
                dp[i][j] = Math.min(Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1), dp[i - 1][j - 1] + cost);
            }
        }
        
        return dp[s1.length()][s2.length()];
    }
    
    /**
     * Suggests a document type based on extracted data.
     *
     * @param extractedData The extracted data from the document
     * @return The suggested document type, or null if no suggestion can be made
     */
    private DocumentType suggestDocumentType(Map<String, Object> extractedData) {
        if (extractedData == null || extractedData.isEmpty()) {
            return null;
        }
        
        // Check for key fields that indicate specific document types
        if (extractedData.containsKey("accountNumber") && extractedData.containsKey("bankName") && 
            extractedData.containsKey("statementDate")) {
            return DocumentType.BANK_STATEMENT;
        }
        
        if (extractedData.containsKey("taxYear") && extractedData.containsKey("ein") && 
            extractedData.containsKey("grossRevenue")) {
            return DocumentType.TAX_RETURN;
        }
        
        if (extractedData.containsKey("licenseNumber") && extractedData.containsKey("issueDate") && 
            extractedData.containsKey("expirationDate")) {
            return DocumentType.BUSINESS_LICENSE;
        }
        
        if (extractedData.containsKey("idType") && extractedData.containsKey("idNumber") && 
            extractedData.containsKey("dateOfBirth")) {
            return DocumentType.ID_VERIFICATION;
        }
        
        if (extractedData.containsKey("invoiceNumber") && extractedData.containsKey("invoiceDate") && 
            extractedData.containsKey("totalAmount")) {
            return DocumentType.INVOICE;
        }
        
        // Default to miscellaneous if no specific type can be determined
        return DocumentType.MISCELLANEOUS;
    }