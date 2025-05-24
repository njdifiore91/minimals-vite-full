-- Schema for MCA Application Processing System Test Database
-- This script creates the test database schema for the Data Service microservice
-- It defines all necessary tables, enum types, and constraints required for testing

-- Create enum types
CREATE TYPE ApplicationStatus AS ENUM ('PENDING', 'IN_REVIEW', 'APPROVED', 'REJECTED', 'INCOMPLETE');
CREATE TYPE ReviewStatus AS ENUM ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'NEEDS_INFORMATION');
CREATE TYPE DocumentType AS ENUM ('APPLICATION_FORM', 'BANK_STATEMENT', 'TAX_RETURN', 'BUSINESS_LICENSE', 'IDENTITY_DOCUMENT', 'FINANCIAL_STATEMENT', 'OTHER');
CREATE TYPE EventType AS ENUM ('APPLICATION_CREATED', 'APPLICATION_UPDATED', 'APPLICATION_STATUS_CHANGED', 'DOCUMENT_UPLOADED', 'REVIEW_COMPLETED');

-- Create application table
CREATE TABLE application (
    id UUID PRIMARY KEY,
    status ApplicationStatus NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    review_status ReviewStatus NOT NULL
);

-- Create merchant_details table
CREATE TABLE merchant_details (
    id UUID PRIMARY KEY,
    application_id UUID NOT NULL,
    legal_name VARCHAR(255) NOT NULL,
    dba_name VARCHAR(255),
    ein VARCHAR(20) NOT NULL,  -- Encrypted in service layer
    address JSONB NOT NULL,
    industry VARCHAR(100) NOT NULL,
    revenue NUMERIC(15, 2) NOT NULL,
    CONSTRAINT fk_merchant_application FOREIGN KEY (application_id) REFERENCES application(id) ON DELETE CASCADE
);

-- Create document table
CREATE TABLE document (
    id UUID PRIMARY KEY,
    application_id UUID NOT NULL,
    type DocumentType NOT NULL,
    storage_path VARCHAR(512) NOT NULL,
    classification VARCHAR(100),
    uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB,
    CONSTRAINT fk_document_application FOREIGN KEY (application_id) REFERENCES application(id) ON DELETE CASCADE
);

-- Create webhook table
CREATE TABLE webhook (
    id UUID PRIMARY KEY,
    endpoint_url VARCHAR(512) NOT NULL,
    secret_key VARCHAR(255) NOT NULL,  -- Encrypted in service layer
    active BOOLEAN NOT NULL DEFAULT TRUE,
    event_type EventType NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Create indexes for performance optimization
CREATE INDEX idx_application_status ON application(status);
CREATE INDEX idx_application_review_status ON application(review_status);
CREATE INDEX idx_merchant_details_application_id ON merchant_details(application_id);
CREATE INDEX idx_document_application_id ON document(application_id);
CREATE INDEX idx_document_type ON document(type);
CREATE INDEX idx_webhook_event_type ON webhook(event_type);
CREATE INDEX idx_webhook_active ON webhook(active);

-- Note: Field-level encryption for PII (ein, secret_key) is handled in the service layer
-- This schema is automatically executed by Spring Boot's @DataJpaTest to set up an in-memory database for repository tests