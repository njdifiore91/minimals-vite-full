-- V3__add_constraints.sql
-- Adds foreign key constraints to establish referential integrity between tables

-- Add NOT NULL constraint to document.application_id
ALTER TABLE document
    ALTER COLUMN application_id SET NOT NULL;

-- Add foreign key constraint from document.application_id to application.id with CASCADE delete
ALTER TABLE document
    ADD CONSTRAINT fk_document_application
    FOREIGN KEY (application_id)
    REFERENCES application(id)
    ON DELETE CASCADE;

-- Add NOT NULL constraint to merchant_details.application_id
ALTER TABLE merchant_details
    ALTER COLUMN application_id SET NOT NULL;

-- Add unique constraint on merchant_details.application_id to enforce one-to-one relationship
ALTER TABLE merchant_details
    ADD CONSTRAINT uq_merchant_details_application_id
    UNIQUE (application_id);

-- Add foreign key constraint from merchant_details.application_id to application.id with CASCADE delete
ALTER TABLE merchant_details
    ADD CONSTRAINT fk_merchant_details_application
    FOREIGN KEY (application_id)
    REFERENCES application(id)
    ON DELETE CASCADE;

-- Add comment explaining the constraints
COMMENT ON CONSTRAINT fk_document_application ON document IS 'Ensures documents are always associated with valid applications and are deleted when the application is deleted';
COMMENT ON CONSTRAINT fk_merchant_details_application ON merchant_details IS 'Ensures merchant details are always associated with valid applications and are deleted when the application is deleted';
COMMENT ON CONSTRAINT uq_merchant_details_application_id ON merchant_details IS 'Enforces one-to-one relationship between application and merchant details';