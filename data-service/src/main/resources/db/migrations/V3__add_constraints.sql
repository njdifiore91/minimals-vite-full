-- V3__add_constraints.sql
-- Third migration script that establishes referential integrity in the MCA database
-- by adding foreign key constraints between related tables.

-- =============================================
-- Document Table Constraints
-- =============================================

-- Ensure application_id is not null to prevent orphaned documents
ALTER TABLE document
    ALTER COLUMN application_id SET NOT NULL;

-- Add foreign key constraint to ensure documents are associated with valid applications
-- Configure CASCADE delete to automatically remove documents when an application is deleted
ALTER TABLE document
    ADD CONSTRAINT fk_document_application
    FOREIGN KEY (application_id)
    REFERENCES application(id)
    ON DELETE CASCADE;

-- =============================================
-- Merchant Details Table Constraints
-- =============================================

-- Ensure application_id is not null to prevent orphaned merchant details
ALTER TABLE merchant_details
    ALTER COLUMN application_id SET NOT NULL;

-- Add unique constraint to enforce one-to-one relationship between
-- application and merchant details (one application can have only one merchant details record)
ALTER TABLE merchant_details
    ADD CONSTRAINT uk_merchant_details_application_id
    UNIQUE (application_id);

-- Add foreign key constraint to ensure merchant details are associated with valid applications
-- Configure CASCADE delete to automatically remove merchant details when an application is deleted
ALTER TABLE merchant_details
    ADD CONSTRAINT fk_merchant_details_application
    FOREIGN KEY (application_id)
    REFERENCES application(id)
    ON DELETE CASCADE;