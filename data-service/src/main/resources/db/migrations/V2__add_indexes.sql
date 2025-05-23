-- V2__add_indexes.sql
-- Second migration script that adds performance-optimizing indexes to the MCA database schema.
-- These indexes improve query performance for common access patterns and are critical
-- for maintaining performance as the database grows with production usage.

-- =============================================
-- Application Table Indexes
-- =============================================

-- Index for filtering applications by status
-- Improves performance for queries that filter by application status
CREATE INDEX idx_application_status ON application(status);

-- Index for filtering applications by review status
-- Improves performance for queries that filter by review state
CREATE INDEX idx_application_review_status ON application(review_status);

-- Index for date-based queries and sorting on application creation date
-- Improves performance for queries that sort or filter by creation date
CREATE INDEX idx_application_created_at ON application(created_at);

-- =============================================
-- Document Table Indexes
-- =============================================

-- Index for efficient document retrieval by application
-- Improves performance for queries that retrieve all documents for a specific application
CREATE INDEX idx_document_application_id ON document(application_id);

-- Index for filtering documents by type
-- Improves performance for queries that filter documents by their type
CREATE INDEX idx_document_type ON document(type);

-- Index for filtering by classification confidence
-- Improves performance for queries that filter documents by their classification
CREATE INDEX idx_document_classification ON document(classification);

-- Index for date-based queries and sorting on document upload date
-- Improves performance for queries that sort or filter by upload date
CREATE INDEX idx_document_uploaded_at ON document(uploaded_at);

-- =============================================
-- Merchant Details Table Indexes
-- =============================================

-- Index for efficient merchant details retrieval by application
-- Improves performance for queries that retrieve merchant details for a specific application
CREATE INDEX idx_merchant_details_application_id ON merchant_details(application_id);

-- =============================================
-- Webhook Table Indexes
-- =============================================

-- Index for filtering webhooks by event type
-- Improves performance for queries that filter webhooks by their event type
CREATE INDEX idx_webhook_event_type ON webhook(event_type);

-- Index for filtering active webhooks
-- Improves performance for queries that filter active webhooks
CREATE INDEX idx_webhook_active ON webhook(active);