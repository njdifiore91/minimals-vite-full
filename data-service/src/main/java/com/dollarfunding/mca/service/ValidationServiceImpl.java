package com.dollarfunding.mca.service;

import com.dollarfunding.mca.dto.ErrorResponseDTO.ValidationError;
import com.dollarfunding.mca.dto.MerchantDetailsRequestDTO;
import com.dollarfunding.mca.entity.Application;
import com.dollarfunding.mca.entity.Document;
import com.dollarfunding.mca.entity.DocumentType;
import com.dollarfunding.mca.exception.ValidationException;
import com.dollarfunding.mca.repository.ApplicationRepository;
import com.dollarfunding.mca.repository.DocumentRepository;
import com.dollarfunding.mca.util.JsonUtil;
import com.dollarfunding.mca.util.JsonUtil.JsonConversionException;
import com.dollarfunding.mca.util.JsonUtil.JsonValidationResult;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import javax.annotation.PostConstruct;
import javax.validation.ConstraintViolation;
import javax.validation.Validator;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * Implementation of the ValidationService interface that handles data validation
 * and business rule application for the MCA application.
 * <p>
 * This service validates application data, document data, and merchant details against
 * predefined schemas and business rules. It implements configurable validation rules
 * and provides detailed validation results with error messages and validation status.
 * </p>
 * <p>
 * The service uses JSON Schema validation for structural validation and applies
 * business rules for semantic validation. It also supports caching of validation
 * results for improved performance.
 * </p>
 *
 * @author MCA Application Team
 */
@Service
public class ValidationServiceImpl implements ValidationService {

    private static final Logger logger = LoggerFactory.getLogger(ValidationServiceImpl.class);

    private final Map<String, String> schemaCache = new ConcurrentHashMap<>();
    private final Map<String, List<BusinessRule>> businessRules = new ConcurrentHashMap<>();

    private final ApplicationRepository applicationRepository;
    private final DocumentRepository documentRepository;
    private final Validator validator;
    private final ObjectMapper objectMapper;

    /**
     * Constructor for ValidationServiceImpl.
     *
     * @param applicationRepository Repository for application data
     * @param documentRepository    Repository for document data
     * @param validator             Bean validation validator
     * @param objectMapper          Jackson ObjectMapper for JSON processing
     */
    @Autowired
    public ValidationServiceImpl(ApplicationRepository applicationRepository,
                                 DocumentRepository documentRepository,
                                 Validator validator,
                                 ObjectMapper objectMapper) {
        this.applicationRepository = applicationRepository;
        this.documentRepository = documentRepository;
        this.validator = validator;
        this.objectMapper = objectMapper;
    }

    /**
     * Initializes the validation service by loading schemas and business rules.
     */
    @PostConstruct
    public void init() {
        loadSchemas();
        initializeBusinessRules();
    }

    /**
     * Loads JSON schemas from the classpath resources.
     */
    private void loadSchemas() {
        try {
            // Load application schema
            loadSchema("application", "schemas/application-schema.json");
            
            // Load document schemas for each document type
            for (DocumentType type : DocumentType.values()) {
                String schemaPath = "schemas/document-" + type.name().toLowerCase() + "-schema.json";
                loadSchema("document-" + type.name().toLowerCase(), schemaPath);
            }
            
            // Load merchant details schema
            loadSchema("merchant", "schemas/merchant-schema.json");
            
            logger.info("Successfully loaded {} JSON schemas", schemaCache.size());
        } catch (Exception e) {
            logger.error("Failed to load JSON schemas", e);
        }
    }

    /**
     * Loads a single schema from the classpath resources.
     *
     * @param schemaName The name to identify the schema
     * @param schemaPath The path to the schema resource
     */
    private void loadSchema(String schemaName, String schemaPath) {
        try {
            Resource resource = new ClassPathResource(schemaPath);
            if (resource.exists()) {
                try (InputStream inputStream = resource.getInputStream()) {
                    String schemaContent = new String(inputStream.readAllBytes(), StandardCharsets.UTF_8);
                    schemaCache.put(schemaName, schemaContent);
                    logger.debug("Loaded schema: {}", schemaName);
                }
            } else {
                logger.warn("Schema not found: {}", schemaPath);
            }
        } catch (IOException e) {
            logger.error("Failed to load schema: {}", schemaPath, e);
        }
    }

    /**
     * Initializes business rules for different entity types.
     */
    private void initializeBusinessRules() {
        // Application business rules
        List<BusinessRule> applicationRules = new ArrayList<>();
        applicationRules.add(new BusinessRule("status_transition", "Invalid status transition",
                data -> {
                    try {
                        JsonNode node = objectMapper.readTree(data.toString());
                        if (node.has("status") && node.has("current_status")) {
                            String newStatus = node.get("status").asText();
                            String currentStatus = node.get("current_status").asText();
                            return isValidStatusTransition(currentStatus, newStatus);
                        }
                        return true;
                    } catch (Exception e) {
                        logger.error("Error applying status transition rule", e);
                        return false;
                    }
                }));
        businessRules.put("application", applicationRules);

        // Merchant details business rules
        List<BusinessRule> merchantRules = new ArrayList<>();
        merchantRules.add(new BusinessRule("revenue_threshold", "Revenue must be at least $50,000 for funding",
                data -> {
                    try {
                        if (data instanceof MerchantDetailsRequestDTO) {
                            MerchantDetailsRequestDTO merchant = (MerchantDetailsRequestDTO) data;
                            return merchant.getRevenue() == null || merchant.getRevenue().doubleValue() >= 50000.0;
                        }
                        return true;
                    } catch (Exception e) {
                        logger.error("Error applying revenue threshold rule", e);
                        return false;
                    }
                }));
        businessRules.put("merchant", merchantRules);

        // Document business rules
        List<BusinessRule> documentRules = new ArrayList<>();
        documentRules.add(new BusinessRule("confidence_threshold", "Document confidence score below threshold",
                data -> {
                    try {
                        JsonNode node = objectMapper.readTree(data.toString());
                        if (node.has("confidenceScores") && node.has("type")) {
                            String type = node.get("type").asText();
                            DocumentType docType = DocumentType.valueOf(type);
                            double threshold = docType.getOcrConfidenceThreshold();
                            
                            JsonNode scores = node.get("confidenceScores");
                            if (scores.has("classification")) {
                                double score = scores.get("classification").asDouble();
                                return score >= threshold;
                            }
                        }
                        return true;
                    } catch (Exception e) {
                        logger.error("Error applying confidence threshold rule", e);
                        return false;
                    }
                }));
        businessRules.put("document", documentRules);

        logger.info("Initialized business rules for {} entity types", businessRules.size());
    }

    /**
     * Validates merchant data against predefined schemas and business rules.
     *
     * @param merchantDetailsRequestDTO The merchant data to validate
     * @throws ValidationException if validation fails
     */
    @Override
    public void validateMerchantData(MerchantDetailsRequestDTO merchantDetailsRequestDTO) throws ValidationException {
        logger.debug("Validating merchant data");
        
        // Bean validation
        Set<ConstraintViolation<MerchantDetailsRequestDTO>> violations = validator.validate(merchantDetailsRequestDTO);
        if (!violations.isEmpty()) {
            List<ValidationError> errors = violations.stream()
                    .map(violation -> new ValidationError(
                            violation.getPropertyPath().toString(),
                            violation.getMessage()))
                    .collect(Collectors.toList());
            
            throw new ValidationException("Merchant data validation failed", errors);
        }
        
        // Schema validation
        try {
            String merchantJson = objectMapper.writeValueAsString(merchantDetailsRequestDTO);
            String schema = schemaCache.get("merchant");
            
            if (schema != null) {
                JsonValidationResult result = JsonUtil.validateJson(merchantJson, schema);
                if (!result.isValid()) {
                    throw new ValidationException("Merchant data schema validation failed", "schema", result.getMessage());
                }
            }
        } catch (JsonProcessingException e) {
            throw new ValidationException("Failed to serialize merchant data for validation", e);
        } catch (JsonConversionException e) {
            throw new ValidationException("Failed to validate merchant data against schema", e);
        }
        
        // Business rule validation
        List<BusinessRule> rules = businessRules.get("merchant");
        if (rules != null) {
            for (BusinessRule rule : rules) {
                if (!rule.apply(merchantDetailsRequestDTO)) {
                    throw new ValidationException("Business rule validation failed", rule.getName(), rule.getMessage());
                }
            }
        }
        
        logger.debug("Merchant data validation successful");
    }

    /**
     * Validates application data against predefined schemas and business rules.
     *
     * @param applicationData The application data to validate
     * @throws ValidationException if validation fails
     */
    @Override
    public void validateApplicationData(Object applicationData) throws ValidationException {
        logger.debug("Validating application data");
        
        // Schema validation
        try {
            String applicationJson = objectMapper.writeValueAsString(applicationData);
            String schema = schemaCache.get("application");
            
            if (schema != null) {
                JsonValidationResult result = JsonUtil.validateJson(applicationJson, schema);
                if (!result.isValid()) {
                    throw new ValidationException("Application data schema validation failed", "schema", result.getMessage());
                }
            }
        } catch (JsonProcessingException e) {
            throw new ValidationException("Failed to serialize application data for validation", e);
        } catch (JsonConversionException e) {
            throw new ValidationException("Failed to validate application data against schema", e);
        }
        
        // Business rule validation
        List<BusinessRule> rules = businessRules.get("application");
        if (rules != null) {
            for (BusinessRule rule : rules) {
                if (!rule.apply(applicationData)) {
                    throw new ValidationException("Business rule validation failed", rule.getName(), rule.getMessage());
                }
            }
        }
        
        logger.debug("Application data validation successful");
    }

    /**
     * Validates document data against predefined schemas and business rules.
     *
     * @param documentData The document data to validate
     * @throws ValidationException if validation fails
     */
    @Override
    public void validateDocumentData(Object documentData) throws ValidationException {
        logger.debug("Validating document data");
        
        // Extract document type for schema selection
        DocumentType documentType = null;
        try {
            JsonNode node = objectMapper.valueToTree(documentData);
            if (node.has("type")) {
                String typeStr = node.get("type").asText();
                documentType = DocumentType.valueOf(typeStr);
            }
        } catch (IllegalArgumentException e) {
            throw new ValidationException("Invalid document type", "type", "Document type is not recognized");
        } catch (Exception e) {
            throw new ValidationException("Failed to extract document type", e);
        }
        
        // Schema validation
        try {
            String documentJson = objectMapper.writeValueAsString(documentData);
            String schemaKey = documentType != null ? 
                    "document-" + documentType.name().toLowerCase() : "document";
            String schema = schemaCache.get(schemaKey);
            
            if (schema != null) {
                JsonValidationResult result = JsonUtil.validateJson(documentJson, schema);
                if (!result.isValid()) {
                    throw new ValidationException("Document data schema validation failed", "schema", result.getMessage());
                }
            }
        } catch (JsonProcessingException e) {
            throw new ValidationException("Failed to serialize document data for validation", e);
        } catch (JsonConversionException e) {
            throw new ValidationException("Failed to validate document data against schema", e);
        }
        
        // Business rule validation
        List<BusinessRule> rules = businessRules.get("document");
        if (rules != null) {
            for (BusinessRule rule : rules) {
                if (!rule.apply(documentData)) {
                    throw new ValidationException("Business rule validation failed", rule.getName(), rule.getMessage());
                }
            }
        }
        
        logger.debug("Document data validation successful");
    }

    /**
     * Applies business rules to determine if an application is complete and ready for processing.
     *
     * @param applicationId The ID of the application to check
     * @return true if the application is complete, false otherwise
     */
    @Override
    @Cacheable(value = "applicationCompleteness", key = "#applicationId")
    public boolean isApplicationComplete(Object applicationId) {
        logger.debug("Checking if application is complete: {}", applicationId);
        
        if (applicationId == null) {
            return false;
        }
        
        UUID appId;
        try {
            if (applicationId instanceof UUID) {
                appId = (UUID) applicationId;
            } else if (applicationId instanceof String) {
                appId = UUID.fromString((String) applicationId);
            } else {
                appId = UUID.fromString(applicationId.toString());
            }
        } catch (IllegalArgumentException e) {
            logger.error("Invalid application ID format: {}", applicationId, e);
            return false;
        }
        
        // Check if application exists
        Optional<Application> applicationOpt = applicationRepository.findById(appId);
        if (applicationOpt.isEmpty()) {
            logger.warn("Application not found: {}", appId);
            return false;
        }
        
        Application application = applicationOpt.get();
        
        // Check if application has merchant details
        if (application.getMerchantDetails() == null) {
            logger.debug("Application {} is incomplete: missing merchant details", appId);
            return false;
        }
        
        // Check if application has all required documents
        if (!hasRequiredDocuments(appId)) {
            logger.debug("Application {} is incomplete: missing required documents", appId);
            return false;
        }
        
        // Check if all documents have been processed with sufficient confidence
        List<Document> documents = documentRepository.findByApplicationId(appId);
        for (Document document : documents) {
            Map<String, Double> confidenceScores = document.getConfidenceScores();
            if (confidenceScores.isEmpty()) {
                logger.debug("Application {} is incomplete: document {} has no confidence scores", appId, document.getId());
                return false;
            }
            
            double threshold = document.getOcrConfidenceThreshold();
            for (Map.Entry<String, Double> entry : confidenceScores.entrySet()) {
                if (entry.getValue() < threshold) {
                    logger.debug("Application {} is incomplete: document {} has low confidence for field {}", 
                            appId, document.getId(), entry.getKey());
                    return false;
                }
            }
        }
        
        logger.debug("Application {} is complete", appId);
        return true;
    }

    /**
     * Validates that all required documents are present for an application.
     *
     * @param applicationId The ID of the application to check
     * @return true if all required documents are present, false otherwise
     */
    @Override
    @Cacheable(value = "requiredDocuments", key = "#applicationId")
    public boolean hasRequiredDocuments(Object applicationId) {
        logger.debug("Checking if application has required documents: {}", applicationId);
        
        if (applicationId == null) {
            return false;
        }
        
        UUID appId;
        try {
            if (applicationId instanceof UUID) {
                appId = (UUID) applicationId;
            } else if (applicationId instanceof String) {
                appId = UUID.fromString((String) applicationId);
            } else {
                appId = UUID.fromString(applicationId.toString());
            }
        } catch (IllegalArgumentException e) {
            logger.error("Invalid application ID format: {}", applicationId, e);
            return false;
        }
        
        // Check if application exists
        Optional<Application> applicationOpt = applicationRepository.findById(appId);
        if (applicationOpt.isEmpty()) {
            logger.warn("Application not found: {}", appId);
            return false;
        }
        
        // Get all documents for the application
        List<Document> documents = documentRepository.findByApplicationId(appId);
        if (documents.isEmpty()) {
            logger.debug("Application {} has no documents", appId);
            return false;
        }
        
        // Check for required document types
        boolean hasIdentification = false;
        boolean hasFinancial = false;
        boolean hasBusinessVerification = false;
        
        for (Document document : documents) {
            DocumentType type = document.getType();
            if (type == DocumentType.ID_VERIFICATION) {
                hasIdentification = true;
            } else if (type == DocumentType.BANK_STATEMENT || type == DocumentType.TAX_RETURN) {
                hasFinancial = true;
            } else if (type == DocumentType.BUSINESS_LICENSE || type == DocumentType.INVOICE) {
                hasBusinessVerification = true;
            }
        }
        
        boolean hasAllRequired = hasIdentification && hasFinancial && hasBusinessVerification;
        logger.debug("Application {} has required documents: {}", appId, hasAllRequired);
        return hasAllRequired;
    }

    /**
     * Validates if a status transition is valid based on business rules.
     *
     * @param currentStatus The current status of the application
     * @param newStatus     The new status to transition to
     * @return true if the transition is valid, false otherwise
     */
    private boolean isValidStatusTransition(String currentStatus, String newStatus) {
        if (StringUtils.isEmpty(currentStatus) || StringUtils.isEmpty(newStatus)) {
            return false;
        }
        
        // Define valid transitions based on business rules
        Map<String, List<String>> validTransitions = new HashMap<>();
        validTransitions.put("NEW", Arrays.asList("PENDING", "PROCESSING", "REJECTED"));
        validTransitions.put("PENDING", Arrays.asList("PROCESSING", "REJECTED"));
        validTransitions.put("PROCESSING", Arrays.asList("APPROVED", "REJECTED", "PENDING"));
        validTransitions.put("APPROVED", Collections.singletonList("COMPLETED"));
        validTransitions.put("REJECTED", Collections.singletonList("COMPLETED"));
        validTransitions.put("COMPLETED", Collections.emptyList());
        
        List<String> allowedTransitions = validTransitions.getOrDefault(currentStatus.toUpperCase(), Collections.emptyList());
        return allowedTransitions.contains(newStatus.toUpperCase());
    }

    /**
     * Adds a custom business rule for a specific entity type.
     *
     * @param entityType The entity type to add the rule for (e.g., "application", "document", "merchant")
     * @param rule       The business rule to add
     */
    public void addBusinessRule(String entityType, BusinessRule rule) {
        if (!businessRules.containsKey(entityType)) {
            businessRules.put(entityType, new ArrayList<>());
        }
        businessRules.get(entityType).add(rule);
        logger.info("Added business rule '{}' for entity type '{}'", rule.getName(), entityType);
    }

    /**
     * Removes a business rule for a specific entity type.
     *
     * @param entityType The entity type to remove the rule from
     * @param ruleName   The name of the rule to remove
     * @return true if the rule was removed, false otherwise
     */
    public boolean removeBusinessRule(String entityType, String ruleName) {
        if (!businessRules.containsKey(entityType)) {
            return false;
        }
        
        List<BusinessRule> rules = businessRules.get(entityType);
        boolean removed = rules.removeIf(rule -> rule.getName().equals(ruleName));
        
        if (removed) {
            logger.info("Removed business rule '{}' for entity type '{}'", ruleName, entityType);
        }
        
        return removed;
    }

    /**
     * Gets all business rules for a specific entity type.
     *
     * @param entityType The entity type to get rules for
     * @return A list of business rules for the entity type
     */
    public List<BusinessRule> getBusinessRules(String entityType) {
        return businessRules.getOrDefault(entityType, Collections.emptyList());
    }

    /**
     * Class representing a business rule with a name, message, and validation function.
     */
    public static class BusinessRule {
        private final String name;
        private final String message;
        private final BusinessRuleFunction function;

        /**
         * Constructor for BusinessRule.
         *
         * @param name     The name of the rule
         * @param message  The error message for the rule
         * @param function The validation function for the rule
         */
        public BusinessRule(String name, String message, BusinessRuleFunction function) {
            this.name = name;
            this.message = message;
            this.function = function;
        }

        /**
         * Gets the name of the rule.
         *
         * @return The rule name
         */
        public String getName() {
            return name;
        }

        /**
         * Gets the error message for the rule.
         *
         * @return The error message
         */
        public String getMessage() {
            return message;
        }

        /**
         * Applies the rule to the provided data.
         *
         * @param data The data to validate
         * @return true if the data passes validation, false otherwise
         */
        public boolean apply(Object data) {
            return function.validate(data);
        }
    }

    /**
     * Functional interface for business rule validation functions.
     */
    @FunctionalInterface
    public interface BusinessRuleFunction {
        /**
         * Validates the provided data against a business rule.
         *
         * @param data The data to validate
         * @return true if the data passes validation, false otherwise
         */
        boolean validate(Object data);
    }
}