-- reset.sql
-- Database reset script for test execution
-- This script truncates all tables while maintaining the schema structure
-- Used between test executions to ensure a clean state

-- Start a transaction for atomic execution
BEGIN;

-- Truncate tables in the correct order to respect foreign key constraints
-- Child tables first, then parent tables

-- 1. Truncate webhook_delivery_log (depends on webhook, application, and document)
TRUNCATE TABLE webhook_delivery_log CASCADE;

-- 2. Truncate processing_event (depends on application and document)
TRUNCATE TABLE processing_event CASCADE;

-- 3. Truncate document (depends on application)
TRUNCATE TABLE document CASCADE;

-- 4. Truncate merchant_details (depends on application)
TRUNCATE TABLE merchant_details CASCADE;

-- 5. Truncate webhook (independent)
TRUNCATE TABLE webhook CASCADE;

-- 6. Truncate application (parent table)
TRUNCATE TABLE application CASCADE;

-- Note: We don't need to reset sequence generators for primary keys
-- because the tables use UUID with gen_random_uuid() as default values

-- Commit the transaction
COMMIT;

-- Usage: This script should be executed between test cases to ensure
-- test isolation without having to recreate the entire schema.
-- Example usage in a Spring Boot test:
--
-- @Sql("/db/reset.sql")
-- @Test
-- public void testSomething() {
--     // Test with a clean database state
-- }