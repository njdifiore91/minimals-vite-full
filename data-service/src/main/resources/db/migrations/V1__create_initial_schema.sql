-- V1__create_initial_schema.sql
-- Initial database migration script for MCA application processing system
-- Creates the core schema including enum types and primary tables

-- Create enum types
CREATE TYPE application_status AS ENUM (
    'PENDING',
    'IN_REVIEW',
    'APPROVED',
    'REJECTED',
    'INCOMPLETE',
    'WITHDRAWN'
);

CREATE TYPE review_status AS ENUM (
    'NOT_STARTED',
    'IN_PROGRESS',
    'COMPLETED',
    'NEEDS_INFORMATION',
    'ESCALATED'
);

CREATE TYPE document_type AS ENUM (
    'APPLICATION_FORM',
    'BANK_STATEMENT',
    'TAX_RETURN',
    'BUSINESS_LICENSE',
    'IDENTITY_DOCUMENT',
    'FINANCIAL_STATEMENT',
    'CREDIT_REPORT',
    'UTILITY_BILL',
    'LEASE_AGREEMENT',
    'OTHER'
);

CREATE TYPE document_status AS ENUM (
    'PENDING',
    'CLASSIFICATION_IN_PROGRESS',
    'CLASSIFICATION_FAILED',
    'CLASSIFICATION_COMPLETED',
    'OCR_IN_PROGRESS',
    'OCR_FAILED',
    'OCR_COMPLETED',
    'VALIDATION_IN_PROGRESS',
    'VALIDATION_FAILED',
    'VALIDATION_COMPLETED',
    'MANUAL_REVIEW_REQUIRED',
    'MANUAL_REVIEW_COMPLETED',
    'COMPLETED',
    'ERROR'
);

CREATE TYPE event_type AS ENUM (
    'APPLICATION_CREATED',
    'APPLICATION_UPDATED',
    'APPLICATION_STATUS_CHANGED',
    'DOCUMENT_UPLOADED',
    'DOCUMENT_CLASSIFIED',
    'DOCUMENT_CLASSIFICATION_FAILED',
    'DOCUMENT_OCR_STARTED',
    'DOCUMENT_OCR_COMPLETED',
    'DOCUMENT_OCR_FAILED',
    'DOCUMENT_VALIDATION_COMPLETED',
    'DOCUMENT_VALIDATION_FAILED',
    'DOCUMENT_MANUAL_REVIEW_REQUIRED',
    'DOCUMENT_MANUAL_REVIEW_COMPLETED',
    'DOCUMENT_PROCESSING_COMPLETED',
    'REVIEW_COMPLETED',
    'WEBHOOK_DELIVERY_ATTEMPTED',
    'WEBHOOK_DELIVERY_SUCCEEDED',
    'WEBHOOK_DELIVERY_FAILED'
);

-- Create application table
CREATE TABLE application (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status application_status NOT NULL DEFAULT 'PENDING',
    metadata JSONB,
    email_source_id VARCHAR(255), -- Reference to the source email ID
    processing_status VARCHAR(50) DEFAULT 'PENDING', -- Overall processing status
    error_message TEXT, -- Error message if processing failed
    retry_count INTEGER DEFAULT 0, -- Number of processing retry attempts
    last_retry_at TIMESTAMP WITH TIME ZONE, -- Last retry timestamp
    completed_at TIMESTAMP WITH TIME ZONE, -- When application processing was completed
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    review_status review_status NOT NULL DEFAULT 'NOT_STARTED'
);

-- Create merchant_details table with PII considerations
CREATE TABLE merchant_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES application(id) ON DELETE CASCADE,
    legal_name VARCHAR(255) NOT NULL, -- PII: Encrypted at application level
    dba_name VARCHAR(255),
    ein VARCHAR(20), -- PII: Encrypted at application level
    address JSONB NOT NULL, -- PII: Contains address information, encrypted at application level
    industry VARCHAR(100),
    revenue NUMERIC(15, 2),
    phone_number VARCHAR(20), -- PII: Encrypted at application level
    email VARCHAR(255), -- PII: Encrypted at application level
    website VARCHAR(255),
    years_in_business INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_application_id UNIQUE (application_id)
);

-- Create document table
CREATE TABLE document (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES application(id) ON DELETE CASCADE,
    type document_type NOT NULL,
    storage_path VARCHAR(512) NOT NULL, -- References S3 storage with AES-256 encryption
    original_filename VARCHAR(255),
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    classification VARCHAR(100),
    classification_confidence NUMERIC(5, 2), -- Confidence score from document classification
    ocr_confidence NUMERIC(5, 2), -- Confidence score from OCR extraction
    status document_status NOT NULL DEFAULT 'PENDING', -- Status of document processing
    error_message TEXT, -- Error message if processing failed
    retry_count INTEGER DEFAULT 0, -- Number of processing retry attempts
    max_retries INTEGER DEFAULT 3, -- Maximum number of retry attempts
    uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    classification_started_at TIMESTAMP WITH TIME ZONE,
    classification_completed_at TIMESTAMP WITH TIME ZONE,
    ocr_started_at TIMESTAMP WITH TIME ZONE,
    ocr_completed_at TIMESTAMP WITH TIME ZONE,
    validation_completed_at TIMESTAMP WITH TIME ZONE,
    manual_review_requested_at TIMESTAMP WITH TIME ZONE,
    manual_review_completed_at TIMESTAMP WITH TIME ZONE,
    manual_review_by VARCHAR(255), -- User who performed manual review
    processed_at TIMESTAMP WITH TIME ZONE, -- When document processing was completed
    metadata JSONB, -- Contains extracted data and processing information
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create processing_event table to track application processing events
CREATE TABLE processing_event (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES application(id) ON DELETE CASCADE,
    document_id UUID REFERENCES document(id) ON DELETE CASCADE,
    event_type event_type NOT NULL,
    event_data JSONB, -- Additional event data
    created_by VARCHAR(255), -- User or service that created the event
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create webhook table for notifications
CREATE TABLE webhook (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint_url VARCHAR(512) NOT NULL,
    secret_key VARCHAR(255) NOT NULL, -- Encrypted at application level for HMAC-SHA256 signing
    description VARCHAR(255),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    event_type event_type NOT NULL,
    retry_count INTEGER DEFAULT 0, -- Number of retry attempts
    max_retries INTEGER DEFAULT 5, -- Maximum number of retry attempts
    retry_delay_seconds INTEGER DEFAULT 60, -- Initial delay between retries in seconds
    last_attempted_at TIMESTAMP WITH TIME ZONE, -- Last delivery attempt timestamp
    last_successful_at TIMESTAMP WITH TIME ZONE, -- Last successful delivery timestamp
    created_by VARCHAR(255), -- User who created the webhook
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create webhook_delivery_log table to track webhook delivery attempts
CREATE TABLE webhook_delivery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id UUID NOT NULL REFERENCES webhook(id) ON DELETE CASCADE,
    application_id UUID REFERENCES application(id) ON DELETE CASCADE,
    document_id UUID REFERENCES document(id) ON DELETE CASCADE,
    event_type event_type NOT NULL,
    payload JSONB NOT NULL, -- The payload that was sent
    status VARCHAR(50) NOT NULL, -- SUCCESS, FAILED
    response_code INTEGER, -- HTTP response code
    response_body TEXT, -- Response from the endpoint
    error_message TEXT, -- Error message if delivery failed
    attempt_number INTEGER NOT NULL, -- Which attempt this was
    next_retry_at TIMESTAMP WITH TIME ZONE, -- When the next retry is scheduled
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_application_status ON application(status);
CREATE INDEX idx_application_review_status ON application(review_status);
CREATE INDEX idx_application_processing_status ON application(processing_status);
CREATE INDEX idx_application_created_at ON application(created_at);
CREATE INDEX idx_application_completed_at ON application(completed_at);

CREATE INDEX idx_merchant_details_application_id ON merchant_details(application_id);
CREATE INDEX idx_merchant_details_legal_name ON merchant_details(legal_name);

CREATE INDEX idx_document_application_id ON document(application_id);
CREATE INDEX idx_document_type ON document(type);
CREATE INDEX idx_document_status ON document(status);
CREATE INDEX idx_document_uploaded_at ON document(uploaded_at);
CREATE INDEX idx_document_processed_at ON document(processed_at);
CREATE INDEX idx_document_classification_confidence ON document(classification_confidence);

CREATE INDEX idx_processing_event_application_id ON processing_event(application_id);
CREATE INDEX idx_processing_event_document_id ON processing_event(document_id);
CREATE INDEX idx_processing_event_event_type ON processing_event(event_type);
CREATE INDEX idx_processing_event_created_at ON processing_event(created_at);

CREATE INDEX idx_webhook_event_type ON webhook(event_type);
CREATE INDEX idx_webhook_active ON webhook(active);

CREATE INDEX idx_webhook_delivery_log_webhook_id ON webhook_delivery_log(webhook_id);
CREATE INDEX idx_webhook_delivery_log_application_id ON webhook_delivery_log(application_id);
CREATE INDEX idx_webhook_delivery_log_document_id ON webhook_delivery_log(document_id);
CREATE INDEX idx_webhook_delivery_log_status ON webhook_delivery_log(status);
CREATE INDEX idx_webhook_delivery_log_created_at ON webhook_delivery_log(created_at);
CREATE INDEX idx_webhook_delivery_log_next_retry_at ON webhook_delivery_log(next_retry_at);

-- Add triggers for automatic updated_at timestamp
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_application_timestamp
BEFORE UPDATE ON application
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_merchant_details_timestamp
BEFORE UPDATE ON merchant_details
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_document_timestamp
BEFORE UPDATE ON document
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_webhook_timestamp
BEFORE UPDATE ON webhook
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- Add comments to indicate PII fields that require encryption at application level
COMMENT ON COLUMN merchant_details.ein IS 'Employer Identification Number - PII that must be encrypted at application level using field-level encryption';
COMMENT ON COLUMN merchant_details.legal_name IS 'Legal business name - PII that must be encrypted at application level using field-level encryption';
COMMENT ON COLUMN merchant_details.address IS 'Business address in JSONB format - Contains PII that must be encrypted at application level using field-level encryption';
COMMENT ON COLUMN merchant_details.phone_number IS 'Business phone number - PII that must be encrypted at application level using field-level encryption';
COMMENT ON COLUMN merchant_details.email IS 'Business email address - PII that must be encrypted at application level using field-level encryption';
COMMENT ON COLUMN webhook.secret_key IS 'Secret key for HMAC-SHA256 webhook payload signing - Must be encrypted at application level';
COMMENT ON COLUMN document.storage_path IS 'Path to document in S3-compatible storage with AES-256 encryption at rest';
COMMENT ON COLUMN document.metadata IS 'Contains extracted document data - May contain PII that should be encrypted at application level';
COMMENT ON COLUMN webhook_delivery_log.payload IS 'JSON payload sent to webhook endpoint - May contain PII that should be encrypted at application level';
COMMENT ON COLUMN processing_event.event_data IS 'Additional event data - May contain PII that should be encrypted at application level';