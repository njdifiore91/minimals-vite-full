-- Test data for MCA Application Processing System
-- This script populates the test database with sample data for testing the Data Service microservice

-- Clear existing data (if any)
DELETE FROM webhook;
DELETE FROM document;
DELETE FROM merchant_details;
DELETE FROM application;

-- Application data with different statuses and review states
INSERT INTO application (id, status, review_status, metadata, created_at, updated_at) VALUES 
('app-001', 'NEW', 'NOT_REVIEWED', '{"source": "email", "priority": "high", "agent_notes": "Received via submissions@dollarfunding.com"}', '2025-05-01 09:00:00', '2025-05-01 09:00:00'),
('app-002', 'PENDING', 'IN_REVIEW', '{"source": "email", "priority": "medium", "agent_notes": "Missing tax returns"}', '2025-05-01 10:15:00', '2025-05-01 14:30:00'),
('app-003', 'PROCESSING', 'IN_REVIEW', '{"source": "email", "priority": "high", "agent_notes": "Expedited processing requested"}', '2025-05-02 08:45:00', '2025-05-02 09:30:00'),
('app-004', 'APPROVED', 'APPROVED', '{"source": "email", "priority": "medium", "agent_notes": "Approved for $50,000", "approval_date": "2025-05-03"}', '2025-05-02 11:20:00', '2025-05-03 15:45:00'),
('app-005', 'REJECTED', 'REJECTED', '{"source": "email", "priority": "low", "agent_notes": "Insufficient revenue", "rejection_reason": "Low monthly revenue"}', '2025-05-02 13:10:00', '2025-05-03 10:30:00'),
('app-006', 'COMPLETED', 'APPROVED', '{"source": "email", "priority": "high", "agent_notes": "Funding completed", "funding_date": "2025-05-04", "funding_amount": 75000}', '2025-05-03 09:25:00', '2025-05-04 16:15:00'),
('app-007', 'PENDING', 'NEEDS_INFORMATION', '{"source": "email", "priority": "medium", "agent_notes": "Waiting for bank statements", "requested_documents": ["bank_statements", "business_license"]}', '2025-05-03 14:40:00', '2025-05-03 16:20:00'),
('app-008', 'NEW', 'NOT_REVIEWED', '{"source": "email", "priority": "low"}', '2025-05-04 08:30:00', '2025-05-04 08:30:00'),
('app-009', 'PROCESSING', 'IN_REVIEW', '{"source": "email", "priority": "high", "agent_notes": "Large funding request", "requested_amount": 150000}', '2025-05-04 10:45:00', '2025-05-04 13:15:00'),
('app-010', 'PENDING', 'IN_REVIEW', '{"source": "email", "priority": "medium", "agent_notes": "Waiting for verification"}', '2025-05-04 15:20:00', '2025-05-04 16:45:00');

-- Merchant details data with various business types and revenue ranges
INSERT INTO merchant_details (id, application_id, legal_name, dba_name, ein, address, industry, revenue) VALUES
('md-001', 'app-001', 'Acme Corporation', 'Acme', '12-3456789', '{"street": "123 Main St", "city": "New York", "state": "NY", "zip": "10001", "country": "USA"}', 'RETAIL', 1250000),
('md-002', 'app-002', 'Beta Enterprises LLC', 'Beta Shop', '23-4567890', '{"street": "456 Market St", "city": "San Francisco", "state": "CA", "zip": "94103", "country": "USA"}', 'TECHNOLOGY', 3500000),
('md-003', 'app-003', 'Gamma Services Inc', 'Gamma', '34-5678901', '{"street": "789 Oak Ave", "city": "Chicago", "state": "IL", "zip": "60601", "country": "USA"}', 'SERVICES', 750000),
('md-004', 'app-004', 'Delta Manufacturing Co', 'Delta Mfg', '45-6789012', '{"street": "101 Industrial Blvd", "city": "Detroit", "state": "MI", "zip": "48201", "country": "USA"}', 'MANUFACTURING', 5200000),
('md-005', 'app-005', 'Epsilon Restaurant Group', 'Epsilon Dining', '56-7890123', '{"street": "202 Culinary Way", "city": "Los Angeles", "state": "CA", "zip": "90001", "country": "USA"}', 'FOOD_SERVICE', 450000),
('md-006', 'app-006', 'Zeta Construction LLC', 'Zeta Builders', '67-8901234', '{"street": "303 Builder Ave", "city": "Houston", "state": "TX", "zip": "77001", "country": "USA"}', 'CONSTRUCTION', 2800000),
('md-007', 'app-007', 'Eta Healthcare Services', 'Eta Health', '78-9012345', '{"street": "404 Medical Dr", "city": "Boston", "state": "MA", "zip": "02101", "country": "USA"}', 'HEALTHCARE', 1900000),
('md-009', 'app-009', 'Theta Logistics Inc', 'Theta Transport', '90-1234567', '{"street": "606 Shipping Lane", "city": "Miami", "state": "FL", "zip": "33101", "country": "USA"}', 'TRANSPORTATION', 4100000);
-- Note: app-008 and app-010 intentionally don't have merchant details (edge case)

-- Document data with different types, classifications, and metadata
INSERT INTO document (id, application_id, type, storage_path, classification, uploaded_at, metadata) VALUES
('doc-001', 'app-001', 'BANK_STATEMENT', 's3://mca-documents-test/app-001/bank_statement_jan.pdf', 'FINANCIAL', '2025-05-01 09:15:00', '{"pages": 3, "confidence": 0.98, "extracted_data": {"account_number": "*****7890", "bank_name": "First National Bank", "period": "January 2025", "ending_balance": 45678.90}}'),
('doc-002', 'app-001', 'TAX_RETURN', 's3://mca-documents-test/app-001/tax_return_2024.pdf', 'FINANCIAL', '2025-05-01 09:20:00', '{"pages": 12, "confidence": 0.95, "extracted_data": {"tax_year": "2024", "gross_income": 1250000, "net_income": 320000, "tax_id": "12-3456789"}}'),
('doc-003', 'app-001', 'BUSINESS_LICENSE', 's3://mca-documents-test/app-001/business_license.pdf', 'IDENTIFICATION', '2025-05-01 09:25:00', '{"pages": 1, "confidence": 0.99, "extracted_data": {"license_number": "BL-12345", "issue_date": "2024-01-15", "expiration_date": "2026-01-14", "issuing_authority": "New York Department of Commerce"}}'),
('doc-004', 'app-002', 'BANK_STATEMENT', 's3://mca-documents-test/app-002/bank_statement_feb.pdf', 'FINANCIAL', '2025-05-01 10:30:00', '{"pages": 4, "confidence": 0.97, "extracted_data": {"account_number": "*****2345", "bank_name": "Pacific Banking Corp", "period": "February 2025", "ending_balance": 89012.34}}'),
('doc-005', 'app-002', 'INVOICE', 's3://mca-documents-test/app-002/invoice_123.pdf', 'FINANCIAL', '2025-05-01 10:35:00', '{"pages": 1, "confidence": 0.96, "extracted_data": {"invoice_number": "INV-123", "date": "2025-02-15", "amount": 12500, "customer": "XYZ Corp"}}'),
('doc-006', 'app-003', 'ID_VERIFICATION', 's3://mca-documents-test/app-003/drivers_license.jpg', 'IDENTIFICATION', '2025-05-02 08:50:00', '{"pages": 1, "confidence": 0.94, "extracted_data": {"id_type": "Driver License", "id_number": "DL-987654321", "name": "John Smith", "expiration_date": "2027-05-20", "state": "Illinois"}}'),
('doc-007', 'app-003', 'BANK_STATEMENT', 's3://mca-documents-test/app-003/bank_statement_mar.pdf', 'FINANCIAL', '2025-05-02 08:55:00', '{"pages": 3, "confidence": 0.98, "extracted_data": {"account_number": "*****6789", "bank_name": "Midwest Financial", "period": "March 2025", "ending_balance": 67890.12}}'),
('doc-008', 'app-004', 'TAX_RETURN', 's3://mca-documents-test/app-004/tax_return_2024.pdf', 'FINANCIAL', '2025-05-02 11:30:00', '{"pages": 15, "confidence": 0.93, "extracted_data": {"tax_year": "2024", "gross_income": 5200000, "net_income": 780000, "tax_id": "45-6789012"}}'),
('doc-009', 'app-004', 'BANK_STATEMENT', 's3://mca-documents-test/app-004/bank_statement_apr.pdf', 'FINANCIAL', '2025-05-02 11:35:00', '{"pages": 5, "confidence": 0.97, "extracted_data": {"account_number": "*****3456", "bank_name": "Industrial Credit Union", "period": "April 2025", "ending_balance": 123456.78}}'),
('doc-010', 'app-004', 'BUSINESS_LICENSE', 's3://mca-documents-test/app-004/business_license.pdf', 'IDENTIFICATION', '2025-05-02 11:40:00', '{"pages": 1, "confidence": 0.99, "extracted_data": {"license_number": "BL-67890", "issue_date": "2023-08-10", "expiration_date": "2025-08-09", "issuing_authority": "Michigan Business Bureau"}}'),
('doc-011', 'app-005', 'BANK_STATEMENT', 's3://mca-documents-test/app-005/bank_statement_may.pdf', 'FINANCIAL', '2025-05-02 13:15:00', '{"pages": 2, "confidence": 0.96, "extracted_data": {"account_number": "*****9012", "bank_name": "West Coast Bank", "period": "May 2025", "ending_balance": 23456.78}}'),
('doc-012', 'app-006', 'BANK_STATEMENT', 's3://mca-documents-test/app-006/bank_statement_jun.pdf', 'FINANCIAL', '2025-05-03 09:30:00', '{"pages": 4, "confidence": 0.98, "extracted_data": {"account_number": "*****5678", "bank_name": "Texas Trust", "period": "June 2025", "ending_balance": 234567.89}}'),
('doc-013', 'app-006', 'TAX_RETURN', 's3://mca-documents-test/app-006/tax_return_2024.pdf', 'FINANCIAL', '2025-05-03 09:35:00', '{"pages": 14, "confidence": 0.94, "extracted_data": {"tax_year": "2024", "gross_income": 2800000, "net_income": 560000, "tax_id": "67-8901234"}}'),
('doc-014', 'app-007', 'MISCELLANEOUS', 's3://mca-documents-test/app-007/insurance_certificate.pdf', 'INSURANCE', '2025-05-03 14:45:00', '{"pages": 2, "confidence": 0.92, "extracted_data": {"policy_number": "POL-123456", "insurer": "National Insurance Co", "coverage_amount": 2000000, "expiration_date": "2025-12-31"}}'),
('doc-015', 'app-009', 'BANK_STATEMENT', 's3://mca-documents-test/app-009/bank_statement_jul.pdf', 'FINANCIAL', '2025-05-04 10:50:00', '{"pages": 6, "confidence": 0.97, "extracted_data": {"account_number": "*****1234", "bank_name": "Atlantic Financial", "period": "July 2025", "ending_balance": 345678.90}}'),
('doc-016', 'app-009', 'TAX_RETURN', 's3://mca-documents-test/app-009/tax_return_2024.pdf', 'FINANCIAL', '2025-05-04 10:55:00', '{"pages": 16, "confidence": 0.95, "extracted_data": {"tax_year": "2024", "gross_income": 4100000, "net_income": 820000, "tax_id": "90-1234567"}}'),
('doc-017', 'app-010', 'INVOICE', 's3://mca-documents-test/app-010/invoice_456.pdf', 'FINANCIAL', '2025-05-04 15:25:00', '{"pages": 1, "confidence": 0.93, "extracted_data": {"invoice_number": "INV-456", "date": "2025-04-20", "amount": 45000, "customer": "ABC Industries"}}');
-- Note: app-008 intentionally doesn't have any documents (edge case)

-- Webhook configuration data with different event types and active states
INSERT INTO webhook (id, endpoint_url, secret_key, active, event_type, created_at, updated_at) VALUES
('wh-001', 'https://partner-api.example.com/webhooks/mca-events', 'sk_test_abcdefghijklmnopqrstuvwxyz123456', true, 'APPLICATION_CREATED', '2025-04-15 10:00:00', '2025-04-15 10:00:00'),
('wh-002', 'https://partner-api.example.com/webhooks/mca-events', 'sk_test_abcdefghijklmnopqrstuvwxyz123456', true, 'APPLICATION_UPDATED', '2025-04-15 10:05:00', '2025-04-15 10:05:00'),
('wh-003', 'https://partner-api.example.com/webhooks/mca-events', 'sk_test_abcdefghijklmnopqrstuvwxyz123456', true, 'APPLICATION_APPROVED', '2025-04-15 10:10:00', '2025-04-15 10:10:00'),
('wh-004', 'https://partner-api.example.com/webhooks/mca-events', 'sk_test_abcdefghijklmnopqrstuvwxyz123456', true, 'APPLICATION_REJECTED', '2025-04-15 10:15:00', '2025-04-15 10:15:00'),
('wh-005', 'https://partner-api.example.com/webhooks/mca-events', 'sk_test_abcdefghijklmnopqrstuvwxyz123456', true, 'DOCUMENT_UPLOADED', '2025-04-15 10:20:00', '2025-04-15 10:20:00'),
('wh-006', 'https://partner-api.example.com/webhooks/mca-events', 'sk_test_abcdefghijklmnopqrstuvwxyz123456', true, 'DOCUMENT_PROCESSED', '2025-04-15 10:25:00', '2025-04-15 10:25:00'),
('wh-007', 'https://crm.example.org/api/integrations/mca', 'sk_live_zyxwvutsrqponmlkjihgfedcba654321', true, 'APPLICATION_CREATED', '2025-04-16 09:00:00', '2025-04-16 09:00:00'),
('wh-008', 'https://crm.example.org/api/integrations/mca', 'sk_live_zyxwvutsrqponmlkjihgfedcba654321', true, 'APPLICATION_APPROVED', '2025-04-16 09:05:00', '2025-04-16 09:05:00'),
('wh-009', 'https://crm.example.org/api/integrations/mca', 'sk_live_zyxwvutsrqponmlkjihgfedcba654321', true, 'APPLICATION_REJECTED', '2025-04-16 09:10:00', '2025-04-16 09:10:00'),
('wh-010', 'https://analytics.example.net/webhooks/funding', 'sk_test_analytics_12345abcdef67890ghijklmnop', false, 'APPLICATION_CREATED', '2025-04-17 11:00:00', '2025-04-17 11:00:00'),
('wh-011', 'https://analytics.example.net/webhooks/funding', 'sk_test_analytics_12345abcdef67890ghijklmnop', false, 'APPLICATION_UPDATED', '2025-04-17 11:05:00', '2025-04-17 11:05:00'),
('wh-012', 'https://analytics.example.net/webhooks/funding', 'sk_test_analytics_12345abcdef67890ghijklmnop', false, 'APPLICATION_APPROVED', '2025-04-17 11:10:00', '2025-04-17 11:10:00'),
('wh-013', 'https://notifications.example.io/api/events', 'sk_live_notifications_abcdefghijklmnopqrstuv', true, 'DOCUMENT_UPLOADED', '2025-04-18 14:00:00', '2025-04-18 14:00:00'),
('wh-014', 'https://notifications.example.io/api/events', 'sk_live_notifications_abcdefghijklmnopqrstuv', true, 'DOCUMENT_PROCESSED', '2025-04-18 14:05:00', '2025-04-18 14:05:00');

-- Add comments explaining the test data structure and usage
-- This test data is designed to support various test scenarios including:
-- 1. Applications in different statuses and review states
-- 2. Merchant details with various business types and revenue ranges
-- 3. Documents with different types, classifications, and metadata
-- 4. Webhook configurations with different event types and active states
-- 5. Edge cases such as applications without documents or merchant details
-- 6. Timestamps for testing date-based queries and sorting
--
-- The data supports testing the following requirements:
-- - Process applications in under 5 minutes from receipt to completion
-- - Maintain 99% data extraction accuracy through AI and machine learning
-- - Support filtering applications by status and review status
-- - Support filtering documents by type and classification
-- - Enable efficient retrieval of documents associated with applications
-- - Support webhook delivery to third-party systems with confirmation
-- - Implement role-based permissions for data access