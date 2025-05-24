package com.dollarfunding.mca.util;

/**
 * Application-wide constants for the MCA (Merchant Cash Advance) application.
 * This class centralizes constant values to ensure consistency across the application
 * and simplify maintenance.
 */
public final class Constants {

    private Constants() {
        // Private constructor to prevent instantiation
    }

    /**
     * Application status constants for tracking the state of MCA applications
     * throughout the processing lifecycle.
     */
    public static final class ApplicationStatus {
        public static final String NEW = "NEW";
        public static final String PROCESSING = "PROCESSING";
        public static final String PENDING = "PENDING";
        public static final String APPROVED = "APPROVED";
        public static final String REJECTED = "REJECTED";
        public static final String COMPLETE = "COMPLETE";
        public static final String EXCEPTION = "EXCEPTION";
        public static final String ERROR = "ERROR";
    }

    /**
     * Document type constants for classifying different types of documents
     * with 99% accuracy as specified in requirements.
     */
    public static final class DocumentType {
        public static final String LOAN_APPLICATION = "LOAN_APPLICATION";
        public static final String TAX_RETURN = "TAX_RETURN";
        public static final String BANK_STATEMENT = "BANK_STATEMENT";
        public static final String PAY_STUB = "PAY_STUB";
        public static final String IDENTITY_DOCUMENT = "IDENTITY_DOCUMENT";
        public static final String OTHER = "OTHER";
    }

    /**
     * Standardized error codes for consistent error handling across the application.
     */
    public static final class ErrorCode {
        // General errors
        public static final String GENERAL_ERROR = "GEN-001";
        public static final String VALIDATION_ERROR = "GEN-002";
        public static final String UNAUTHORIZED = "GEN-003";
        public static final String FORBIDDEN = "GEN-004";
        public static final String NOT_FOUND = "GEN-005";
        
        // Application specific errors
        public static final String APPLICATION_NOT_FOUND = "APP-001";
        public static final String APPLICATION_INVALID_STATE = "APP-002";
        public static final String APPLICATION_PROCESSING_ERROR = "APP-003";
        
        // Document specific errors
        public static final String DOCUMENT_NOT_FOUND = "DOC-001";
        public static final String DOCUMENT_INVALID_TYPE = "DOC-002";
        public static final String DOCUMENT_PROCESSING_ERROR = "DOC-003";
        public static final String DOCUMENT_STORAGE_ERROR = "DOC-004";
        
        // OCR specific errors
        public static final String OCR_PROCESSING_ERROR = "OCR-001";
        public static final String OCR_LOW_CONFIDENCE = "OCR-002";
        
        // Data specific errors
        public static final String DATA_VALIDATION_ERROR = "DAT-001";
        public static final String DATA_INTEGRITY_ERROR = "DAT-002";
        
        // Messaging specific errors
        public static final String MESSAGING_PUBLISH_ERROR = "MSG-001";
        public static final String MESSAGING_CONSUME_ERROR = "MSG-002";
    }

    /**
     * Regular expression patterns for common validation requirements.
     */
    public static final class ValidationRegex {
        // Basic patterns
        public static final String EMAIL = "^[\\w-\\.]+@([\\w-]+\\.)+[\\w-]{2,4}$";
        public static final String PHONE = "^\\+?[1-9]\\d{1,14}$"; // E.164 format
        
        // Business identifiers
        public static final String EIN = "^\\d{2}-\\d{7}$"; // Employer Identification Number
        public static final String SSN = "^\\d{3}-\\d{2}-\\d{4}$"; // Social Security Number
        
        // Financial patterns
        public static final String CURRENCY = "^\\$?(\\d{1,3}(\\,\\d{3})*|(\\d+))(\\.\\d{2})?$";
        public static final String PERCENTAGE = "^\\d+(\\.\\d{1,2})?%$";
        
        // Address patterns
        public static final String ZIP_CODE = "^\\d{5}(-\\d{4})?$";
        public static final String STATE_CODE = "^[A-Z]{2}$";
    }

    /**
     * Cache TTL (Time To Live) constants for different types of cached data.
     * Values are in seconds.
     */
    public static final class CacheTTL {
        // Application data: 15 minutes as specified in requirements
        public static final int APPLICATION_DATA = 15 * 60; // 15 minutes in seconds
        
        // User sessions: 24 hours as specified in requirements
        public static final int USER_SESSION = 24 * 60 * 60; // 24 hours in seconds
        
        // Other common cache durations
        public static final int METADATA = 30 * 60; // 30 minutes in seconds
        public static final int CONFIGURATION = 60 * 60; // 1 hour in seconds
    }

    /**
     * RabbitMQ queue and exchange names for service communication.
     */
    public static final class QueueName {
        // Exchange names
        public static final String DOCUMENTS_EXCHANGE = "mca.documents";
        
        // Queue names
        public static final String DOCUMENT_PROCESSING = "document-processing";
        public static final String DATA_EXTRACTION = "data-extraction";
        public static final String NOTIFICATION = "notification";
        
        // Routing keys
        public static final String DOCUMENT_NEW = "document.new";
        public static final String OCR_REQUEST = "ocr.request";
        public static final String DATA_PROCESSING = "data.processing";
    }

    /**
     * Security constants for encryption parameters and other security settings.
     */
    public static final class SecurityConstants {
        // Encryption algorithm for field-level encryption of PII data
        public static final String ENCRYPTION_ALGORITHM = "AES/GCM/NoPadding";
        public static final int AES_KEY_SIZE = 256; // AES-256 as specified in requirements
        public static final int GCM_IV_LENGTH = 12; // GCM recommended IV length
        public static final int GCM_TAG_LENGTH = 16; // GCM authentication tag length
        
        // JWT authentication parameters as specified in requirements
        public static final String JWT_ALGORITHM = "RS256";
        public static final int JWT_EXPIRY = 60; // 60 minutes
        public static final int REFRESH_TOKEN_EXPIRY = 7 * 24 * 60; // 7 days in minutes
        
        // PII field names that require encryption
        public static final String[] PII_FIELDS = {
            "ssn", "ein", "driverLicense", "passportNumber", "bankAccountNumber"
        };
    }

    /**
     * Business rule constants for application processing.
     */
    public static final class BusinessRule {
        // Processing time requirements
        public static final int MAX_PROCESSING_TIME = 5; // 5 minutes maximum processing time
        
        // Automation rate target
        public static final double AUTOMATION_RATE_TARGET = 0.93; // 93% automation rate
        
        // Data extraction accuracy requirement
        public static final double DATA_EXTRACTION_ACCURACY = 0.99; // 99% accuracy
        
        // OCR confidence thresholds
        public static final double OCR_HIGH_CONFIDENCE = 0.75; // 75% and above is high confidence
        public static final double OCR_LOW_CONFIDENCE = 0.50; // Below 50% is low confidence
        
        // Document classification confidence threshold
        public static final double CLASSIFICATION_CONFIDENCE = 0.75; // 75% confidence threshold
    }

    /**
     * API endpoint constants.
     */
    public static final class ApiEndpoint {
        // Base API path
        public static final String API_BASE = "/api/v1";
        
        // Application endpoints
        public static final String APPLICATIONS = API_BASE + "/applications";
        public static final String APPLICATION_BY_ID = APPLICATIONS + "/{id}";
        public static final String APPLICATION_STATUS = APPLICATION_BY_ID + "/status";
        
        // Document endpoints
        public static final String DOCUMENTS = API_BASE + "/documents";
        public static final String DOCUMENT_BY_ID = DOCUMENTS + "/{id}";
        public static final String DOCUMENTS_BY_APPLICATION = APPLICATIONS + "/{id}/documents";
        
        // Webhook endpoints
        public static final String WEBHOOKS = API_BASE + "/webhooks";
        public static final String WEBHOOK_BY_ID = WEBHOOKS + "/{id}";
        public static final String WEBHOOK_TEST = WEBHOOK_BY_ID + "/test";
    }

    /**
     * Configuration key constants.
     */
    public static final class ConfigKey {
        // Database configuration
        public static final String DB_PRIMARY_URL = "spring.datasource.url";
        public static final String DB_USERNAME = "spring.datasource.username";
        public static final String DB_PASSWORD = "spring.datasource.password";
        
        // Redis configuration
        public static final String REDIS_HOST = "spring.redis.host";
        public static final String REDIS_PORT = "spring.redis.port";
        
        // RabbitMQ configuration
        public static final String RABBITMQ_HOST = "spring.rabbitmq.host";
        public static final String RABBITMQ_PORT = "spring.rabbitmq.port";
        public static final String RABBITMQ_USERNAME = "spring.rabbitmq.username";
        public static final String RABBITMQ_PASSWORD = "spring.rabbitmq.password";
        
        // S3 configuration
        public static final String S3_ENDPOINT = "aws.s3.endpoint";
        public static final String S3_REGION = "aws.s3.region";
        public static final String S3_BUCKET = "aws.s3.bucket";
        
        // Security configuration
        public static final String ENCRYPTION_KEY = "security.encryption.key";
        public static final String JWT_PUBLIC_KEY = "security.jwt.public-key";
        public static final String JWT_PRIVATE_KEY = "security.jwt.private-key";
    }
}