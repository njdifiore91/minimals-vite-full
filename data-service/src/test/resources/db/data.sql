-- =============================================
-- MCA Application Processing System Test Data
-- =============================================
-- This script populates the test database with sample data for testing the Data Service microservice.
-- It contains INSERT statements for all tables with representative test data covering various scenarios.
-- This script is automatically executed by Spring Boot's @DataJpaTest after schema.sql to provide
-- consistent test data for repository tests.

-- Begin transaction to ensure data consistency
BEGIN;

-- =============================================
-- Application Data
-- =============================================
-- Applications with different statuses and review states
INSERT INTO application (id, status, review_status, metadata, created_at, updated_at)
VALUES
  -- New application received via email, not yet reviewed
  ('11111111-1111-1111-1111-111111111111', 'PENDING', 'NOT_STARTED', 
   '{"source": "email", "priority": "normal", "submissionId": "EM12345"}', 
   NOW() - INTERVAL '30 minutes', NOW() - INTERVAL '30 minutes'),

  -- Application in review process
  ('22222222-2222-2222-2222-222222222222', 'IN_REVIEW', 'IN_PROGRESS', 
   '{"source": "web", "priority": "high", "submissionId": "WB67890", "assignedTo": "analyst1"}', 
   NOW() - INTERVAL '2 hours', NOW() - INTERVAL '1 hour'),

  -- Approved application with high confidence score
  ('33333333-3333-3333-3333-333333333333', 'APPROVED', 'COMPLETED', 
   '{"source": "email", "priority": "normal", "submissionId": "EM54321", "confidenceScore": 0.98, "processingTimeMs": 240000}', 
   NOW() - INTERVAL '4 hours', NOW() - INTERVAL '3 hours'),

  -- Rejected application due to incomplete documentation
  ('44444444-4444-4444-4444-444444444444', 'REJECTED', 'COMPLETED', 
   '{"source": "web", "priority": "normal", "submissionId": "WB13579", "rejectionReason": "Incomplete documentation", "confidenceScore": 0.45}', 
   NOW() - INTERVAL '5 hours', NOW() - INTERVAL '4 hours'),

  -- Application marked as incomplete, needs additional information
  ('55555555-5555-5555-5555-555555555555', 'INCOMPLETE', 'NEEDS_INFORMATION', 
   '{"source": "email", "priority": "low", "submissionId": "EM24680", "missingDocuments": ["tax_return", "bank_statement"]}', 
   NOW() - INTERVAL '6 hours', NOW() - INTERVAL '5 hours'),

  -- Fast-processed application (under 5 minutes)
  ('66666666-6666-6666-6666-666666666666', 'APPROVED', 'COMPLETED', 
   '{"source": "web", "priority": "high", "submissionId": "WB97531", "confidenceScore": 0.99, "processingTimeMs": 180000, "automationLevel": "full"}', 
   NOW() - INTERVAL '4 minutes', NOW() - INTERVAL '1 minute'),

  -- Application with high confidence score but requiring manual review
  ('77777777-7777-7777-7777-777777777777', 'IN_REVIEW', 'IN_PROGRESS', 
   '{"source": "email", "priority": "high", "submissionId": "EM86420", "confidenceScore": 0.92, "flaggedReason": "Unusual business structure"}', 
   NOW() - INTERVAL '3 hours', NOW() - INTERVAL '2 hours'),

  -- Application with low confidence score requiring manual review
  ('88888888-8888-8888-8888-888888888888', 'IN_REVIEW', 'IN_PROGRESS', 
   '{"source": "web", "priority": "normal", "submissionId": "WB24680", "confidenceScore": 0.65, "flaggedReason": "Inconsistent information"}', 
   NOW() - INTERVAL '7 hours', NOW() - INTERVAL '6 hours'),

  -- Application with no documents (edge case)
  ('99999999-9999-9999-9999-999999999999', 'PENDING', 'NOT_STARTED', 
   '{"source": "email", "priority": "low", "submissionId": "EM99999", "notes": "No documents attached"}', 
   NOW() - INTERVAL '8 hours', NOW() - INTERVAL '8 hours'),

  -- Old application for testing date-based queries
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'APPROVED', 'COMPLETED', 
   '{"source": "web", "priority": "normal", "submissionId": "WB12345", "confidenceScore": 0.97, "processingTimeMs": 300000}', 
   NOW() - INTERVAL '30 days', NOW() - INTERVAL '29 days');

-- =============================================
-- Merchant Details Data
-- =============================================
-- Merchant details with various business types and revenue ranges
INSERT INTO merchant_details (id, application_id, legal_name, dba_name, ein, address, industry, revenue)
VALUES
  -- Retail business with high revenue
  ('11111111-aaaa-1111-aaaa-111111111111', '22222222-2222-2222-2222-222222222222', 
   'ABC Retail Corp', 'ABC Retail', '12-3456789', 
   '{"street": "123 Main St", "city": "Los Angeles", "state": "CA", "zip": "90001", "country": "USA"}', 
   'Retail', 1500000.00),

  -- Food service business with medium revenue
  ('22222222-bbbb-2222-bbbb-222222222222', '33333333-3333-3333-3333-333333333333', 
   'XYZ Food Services LLC', 'XYZ Foods', '98-7654321', 
   '{"street": "456 Broadway", "city": "New York", "state": "NY", "zip": "10001", "country": "USA"}', 
   'Food Service', 750000.00),

  -- Technology business with low revenue
  ('33333333-cccc-3333-cccc-333333333333', '66666666-6666-6666-6666-666666666666', 
   'Tech Innovations Inc', 'TechInno', '45-6789123', 
   '{"street": "789 Tech Blvd", "city": "San Francisco", "state": "CA", "zip": "94105", "country": "USA"}', 
   'Technology', 350000.00),

  -- Manufacturing business with high revenue
  ('44444444-dddd-4444-dddd-444444444444', '77777777-7777-7777-7777-777777777777', 
   'Industrial Manufacturing Co', 'IndManCo', '56-7891234', 
   '{"street": "101 Factory Way", "city": "Detroit", "state": "MI", "zip": "48201", "country": "USA"}', 
   'Manufacturing', 2750000.00),

  -- Healthcare business with medium revenue
  ('55555555-eeee-5555-eeee-555555555555', '88888888-8888-8888-8888-888888888888', 
   'Healthcare Solutions Group', 'HealthSol', '67-8912345', 
   '{"street": "202 Medical Dr", "city": "Boston", "state": "MA", "zip": "02115", "country": "USA"}', 
   'Healthcare', 925000.00),

  -- Construction business with medium revenue
  ('66666666-ffff-6666-ffff-666666666666', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 
   'Build Right Construction LLC', 'Build Right', '78-9123456', 
   '{"street": "303 Builder Ave", "city": "Chicago", "state": "IL", "zip": "60601", "country": "USA"}', 
   'Construction', 1200000.00);

-- =============================================
-- Document Data
-- =============================================
-- Documents with different types, classifications, and metadata
INSERT INTO document (id, application_id, type, storage_path, classification, uploaded_at, metadata)
VALUES
  -- Application form for first application
  ('11111111-1111-aaaa-1111-111111111111', '11111111-1111-1111-1111-111111111111', 
   'APPLICATION_FORM', 'mca-documents-production/application-forms/form-11111111.pdf', 'VERIFIED', 
   NOW() - INTERVAL '30 minutes', 
   '{"confidenceScore": 0.98, "pageCount": 3, "fileSize": 1024000, "mimeType": "application/pdf"}'),

  -- Bank statement for application in review
  ('22222222-2222-bbbb-2222-222222222222', '22222222-2222-2222-2222-222222222222', 
   'BANK_STATEMENT', 'mca-documents-production/bank-statements/statement-22222222.pdf', 'VERIFIED', 
   NOW() - INTERVAL '2 hours', 
   '{"confidenceScore": 0.95, "pageCount": 5, "fileSize": 2048000, "mimeType": "application/pdf", "bankName": "First National Bank", "statementDate": "2023-04-30"}'),

  -- Tax return for application in review
  ('33333333-3333-cccc-3333-333333333333', '22222222-2222-2222-2222-222222222222', 
   'TAX_RETURN', 'mca-documents-production/tax-returns/tax-return-22222222.pdf', 'NEEDS_REVIEW', 
   NOW() - INTERVAL '2 hours', 
   '{"confidenceScore": 0.75, "pageCount": 10, "fileSize": 3072000, "mimeType": "application/pdf", "taxYear": "2022", "formType": "1120"}'),

  -- Business license for application in review
  ('44444444-4444-dddd-4444-444444444444', '22222222-2222-2222-2222-222222222222', 
   'BUSINESS_LICENSE', 'mca-documents-production/business-licenses/license-22222222.jpg', 'VERIFIED', 
   NOW() - INTERVAL '2 hours', 
   '{"confidenceScore": 0.92, "fileSize": 1536000, "mimeType": "image/jpeg", "expirationDate": "2024-12-31", "licenseNumber": "BL-123456"}'),

  -- Application form for approved application
  ('55555555-5555-eeee-5555-555555555555', '33333333-3333-3333-3333-333333333333', 
   'APPLICATION_FORM', 'mca-documents-production/application-forms/form-33333333.pdf', 'VERIFIED', 
   NOW() - INTERVAL '4 hours', 
   '{"confidenceScore": 0.99, "pageCount": 3, "fileSize": 1024000, "mimeType": "application/pdf"}'),

  -- Bank statement for approved application
  ('66666666-6666-ffff-6666-666666666666', '33333333-3333-3333-3333-333333333333', 
   'BANK_STATEMENT', 'mca-documents-production/bank-statements/statement-33333333.pdf', 'VERIFIED', 
   NOW() - INTERVAL '4 hours', 
   '{"confidenceScore": 0.97, "pageCount": 6, "fileSize": 2048000, "mimeType": "application/pdf", "bankName": "Chase Bank", "statementDate": "2023-04-30"}'),

  -- Tax return for approved application
  ('77777777-7777-gggg-7777-777777777777', '33333333-3333-3333-3333-333333333333', 
   'TAX_RETURN', 'mca-documents-production/tax-returns/tax-return-33333333.pdf', 'VERIFIED', 
   NOW() - INTERVAL '4 hours', 
   '{"confidenceScore": 0.96, "pageCount": 12, "fileSize": 3072000, "mimeType": "application/pdf", "taxYear": "2022", "formType": "1120"}'),

  -- Application form for rejected application
  ('88888888-8888-hhhh-8888-888888888888', '44444444-4444-4444-4444-444444444444', 
   'APPLICATION_FORM', 'mca-documents-production/application-forms/form-44444444.pdf', 'VERIFIED', 
   NOW() - INTERVAL '5 hours', 
   '{"confidenceScore": 0.90, "pageCount": 3, "fileSize": 1024000, "mimeType": "application/pdf"}'),

  -- Incomplete bank statement for rejected application
  ('99999999-9999-iiii-9999-999999999999', '44444444-4444-4444-4444-444444444444', 
   'BANK_STATEMENT', 'mca-documents-production/bank-statements/statement-44444444.pdf', 'REJECTED', 
   NOW() - INTERVAL '5 hours', 
   '{"confidenceScore": 0.35, "pageCount": 2, "fileSize": 1024000, "mimeType": "application/pdf", "bankName": "Bank of America", "statementDate": "2023-03-15", "rejectionReason": "Incomplete statement, missing pages"}'),

  -- Application form for incomplete application
  ('aaaaaaaa-aaaa-jjjj-aaaa-aaaaaaaaaaaa', '55555555-5555-5555-5555-555555555555', 
   'APPLICATION_FORM', 'mca-documents-production/application-forms/form-55555555.pdf', 'VERIFIED', 
   NOW() - INTERVAL '6 hours', 
   '{"confidenceScore": 0.94, "pageCount": 3, "fileSize": 1024000, "mimeType": "application/pdf"}'),

  -- Application form for fast-processed application
  ('bbbbbbbb-bbbb-kkkk-bbbb-bbbbbbbbbbbb', '66666666-6666-6666-6666-666666666666', 
   'APPLICATION_FORM', 'mca-documents-production/application-forms/form-66666666.pdf', 'VERIFIED', 
   NOW() - INTERVAL '4 minutes', 
   '{"confidenceScore": 0.99, "pageCount": 3, "fileSize": 1024000, "mimeType": "application/pdf"}'),

  -- Bank statement for fast-processed application
  ('cccccccc-cccc-llll-cccc-cccccccccccc', '66666666-6666-6666-6666-666666666666', 
   'BANK_STATEMENT', 'mca-documents-production/bank-statements/statement-66666666.pdf', 'VERIFIED', 
   NOW() - INTERVAL '4 minutes', 
   '{"confidenceScore": 0.98, "pageCount": 5, "fileSize": 2048000, "mimeType": "application/pdf", "bankName": "Wells Fargo", "statementDate": "2023-04-30"}'),

  -- Tax return for fast-processed application
  ('dddddddd-dddd-mmmm-dddd-dddddddddddd', '66666666-6666-6666-6666-666666666666', 
   'TAX_RETURN', 'mca-documents-production/tax-returns/tax-return-66666666.pdf', 'VERIFIED', 
   NOW() - INTERVAL '4 minutes', 
   '{"confidenceScore": 0.97, "pageCount": 10, "fileSize": 3072000, "mimeType": "application/pdf", "taxYear": "2022", "formType": "1120"}'),

  -- Business license for fast-processed application
  ('eeeeeeee-eeee-nnnn-eeee-eeeeeeeeeeee', '66666666-6666-6666-6666-666666666666', 
   'BUSINESS_LICENSE', 'mca-documents-production/business-licenses/license-66666666.jpg', 'VERIFIED', 
   NOW() - INTERVAL '4 minutes', 
   '{"confidenceScore": 0.99, "fileSize": 1536000, "mimeType": "image/jpeg", "expirationDate": "2025-12-31", "licenseNumber": "BL-789012"}'),

  -- Application form for application requiring manual review
  ('ffffffff-ffff-oooo-ffff-ffffffffffff', '77777777-7777-7777-7777-777777777777', 
   'APPLICATION_FORM', 'mca-documents-production/application-forms/form-77777777.pdf', 'VERIFIED', 
   NOW() - INTERVAL '3 hours', 
   '{"confidenceScore": 0.92, "pageCount": 3, "fileSize": 1024000, "mimeType": "application/pdf"}'),

  -- Bank statement for application requiring manual review
  ('gggggggg-gggg-pppp-gggg-gggggggggggg', '77777777-7777-7777-7777-777777777777', 
   'BANK_STATEMENT', 'mca-documents-production/bank-statements/statement-77777777.pdf', 'NEEDS_REVIEW', 
   NOW() - INTERVAL '3 hours', 
   '{"confidenceScore": 0.72, "pageCount": 5, "fileSize": 2048000, "mimeType": "application/pdf", "bankName": "Citibank", "statementDate": "2023-04-30", "reviewReason": "Unusual transaction patterns"}'),

  -- Business structure document for application requiring manual review
  ('hhhhhhhh-hhhh-qqqq-hhhh-hhhhhhhhhhhh', '77777777-7777-7777-7777-777777777777', 
   'OTHER', 'mca-documents-production/other/structure-77777777.pdf', 'FLAGGED', 
   NOW() - INTERVAL '3 hours', 
   '{"confidenceScore": 0.65, "pageCount": 8, "fileSize": 2048000, "mimeType": "application/pdf", "documentDescription": "Complex business structure diagram", "flagReason": "Unusual ownership structure"}'),

  -- Application form for application with low confidence score
  ('iiiiiiii-iiii-rrrr-iiii-iiiiiiiiiiii', '88888888-8888-8888-8888-888888888888', 
   'APPLICATION_FORM', 'mca-documents-production/application-forms/form-88888888.pdf', 'NEEDS_REVIEW', 
   NOW() - INTERVAL '7 hours', 
   '{"confidenceScore": 0.65, "pageCount": 3, "fileSize": 1024000, "mimeType": "application/pdf", "reviewReason": "Inconsistent information"}'),

  -- Handwritten identity document for application with low confidence score
  ('jjjjjjjj-jjjj-ssss-jjjj-jjjjjjjjjjjj', '88888888-8888-8888-8888-888888888888', 
   'IDENTITY_DOCUMENT', 'mca-documents-production/identity-documents/id-88888888.jpg', 'NEEDS_REVIEW', 
   NOW() - INTERVAL '7 hours', 
   '{"confidenceScore": 0.60, "fileSize": 1536000, "mimeType": "image/jpeg", "idType": "driver_license", "reviewReason": "Handwritten information difficult to extract"}'),

  -- Application form for old application
  ('kkkkkkkk-kkkk-tttt-kkkk-kkkkkkkkkkkk', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 
   'APPLICATION_FORM', 'mca-documents-production/application-forms/form-aaaaaaaa.pdf', 'VERIFIED', 
   NOW() - INTERVAL '30 days', 
   '{"confidenceScore": 0.97, "pageCount": 3, "fileSize": 1024000, "mimeType": "application/pdf"}'),

  -- Bank statement for old application
  ('llllllll-llll-uuuu-llll-llllllllllll', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 
   'BANK_STATEMENT', 'mca-documents-production/bank-statements/statement-aaaaaaaa.pdf', 'VERIFIED', 
   NOW() - INTERVAL '30 days', 
   '{"confidenceScore": 0.96, "pageCount": 5, "fileSize": 2048000, "mimeType": "application/pdf", "bankName": "US Bank", "statementDate": "2023-03-31"}'),

  -- Tax return for old application
  ('mmmmmmmm-mmmm-vvvv-mmmm-mmmmmmmmmmmm', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 
   'TAX_RETURN', 'mca-documents-production/tax-returns/tax-return-aaaaaaaa.pdf', 'VERIFIED', 
   NOW() - INTERVAL '30 days', 
   '{"confidenceScore": 0.95, "pageCount": 10, "fileSize": 3072000, "mimeType": "application/pdf", "taxYear": "2021", "formType": "1120"}'),

  -- Financial statement for old application
  ('nnnnnnnn-nnnn-wwww-nnnn-nnnnnnnnnnnn', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 
   'FINANCIAL_STATEMENT', 'mca-documents-production/financial-statements/statement-aaaaaaaa.pdf', 'VERIFIED', 
   NOW() - INTERVAL '30 days', 
   '{"confidenceScore": 0.94, "pageCount": 15, "fileSize": 4096000, "mimeType": "application/pdf", "statementType": "income_statement", "fiscalYear": "2022"}');

-- =============================================
-- Webhook Data
-- =============================================
-- Webhook configurations with different event types and active states
INSERT INTO webhook (id, endpoint_url, secret_key, active, event_type, created_at, updated_at)
VALUES
  -- Active webhook for application created events
  ('11111111-1111-1111-aaaa-111111111111', 
   'https://example.com/webhooks/applications', 
   'secretKey123456789', 
   TRUE, 
   'APPLICATION_CREATED', 
   NOW() - INTERVAL '30 days', 
   NOW() - INTERVAL '30 days'),

  -- Inactive webhook for application created events
  ('22222222-2222-2222-bbbb-222222222222', 
   'https://example.com/webhooks/inactive', 
   'inactiveSecretKey', 
   FALSE, 
   'APPLICATION_CREATED', 
   NOW() - INTERVAL '25 days', 
   NOW() - INTERVAL '10 days'),

  -- Active webhook for document uploaded events
  ('33333333-3333-3333-cccc-333333333333', 
   'https://example.com/webhooks/documents', 
   'documentSecretKey', 
   TRUE, 
   'DOCUMENT_UPLOADED', 
   NOW() - INTERVAL '20 days', 
   NOW() - INTERVAL '20 days'),

  -- Active webhook for application status changed events
  ('44444444-4444-4444-dddd-444444444444', 
   'https://example.com/webhooks/status', 
   'statusSecretKey', 
   TRUE, 
   'APPLICATION_STATUS_CHANGED', 
   NOW() - INTERVAL '15 days', 
   NOW() - INTERVAL '15 days'),

  -- Active webhook for review completed events
  ('55555555-5555-5555-eeee-555555555555', 
   'https://example.com/webhooks/reviews', 
   'reviewSecretKey', 
   TRUE, 
   'REVIEW_COMPLETED', 
   NOW() - INTERVAL '10 days', 
   NOW() - INTERVAL '10 days'),

  -- Webhook with failures but still within retry limit
  ('66666666-6666-6666-ffff-666666666666', 
   'https://example.com/webhooks/failing', 
   'failingSecretKey', 
   TRUE, 
   'APPLICATION_STATUS_CHANGED', 
   NOW() - INTERVAL '5 days', 
   NOW() - INTERVAL '1 day'),

  -- Webhook that exceeded retry limit
  ('77777777-7777-7777-gggg-777777777777', 
   'https://example.com/webhooks/exceeded', 
   'exceededSecretKey', 
   FALSE, 
   'APPLICATION_STATUS_CHANGED', 
   NOW() - INTERVAL '5 days', 
   NOW() - INTERVAL '1 day');

-- Update webhook failure information
UPDATE webhook SET consecutive_failures = 2, max_retry_attempts = 5, last_failure_at = NOW() - INTERVAL '1 day'
WHERE id = '66666666-6666-6666-ffff-666666666666';

UPDATE webhook SET consecutive_failures = 5, max_retry_attempts = 3, last_failure_at = NOW() - INTERVAL '1 day'
WHERE id = '77777777-7777-7777-gggg-777777777777';

-- Commit transaction
COMMIT;