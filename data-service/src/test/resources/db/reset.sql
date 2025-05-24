-- reset.sql
-- SQL script that resets the test database by truncating all tables while maintaining the schema structure.
-- This script is used between test executions to ensure a clean state without having to recreate the entire schema.
-- It truncates tables in the correct order to respect foreign key constraints (child tables first, then parent tables).

-- Start a transaction to ensure atomic execution
BEGIN;

-- =============================================
-- Truncate child tables first to respect foreign key constraints
-- =============================================

-- Truncate document table (child of application)
TRUNCATE TABLE document CASCADE;

-- Truncate merchant_details table (child of application)
TRUNCATE TABLE merchant_details CASCADE;

-- Truncate webhook table (independent table)
TRUNCATE TABLE webhook CASCADE;

-- =============================================
-- Truncate parent tables after their children
-- =============================================

-- Truncate application table (parent table)
TRUNCATE TABLE application CASCADE;

-- =============================================
-- Reset sequence generators for primary keys
-- =============================================

-- Reset application id sequence
ALTER SEQUENCE application_id_seq RESTART WITH 1;

-- Reset document id sequence
ALTER SEQUENCE document_id_seq RESTART WITH 1;

-- Reset merchant_details id sequence
ALTER SEQUENCE merchant_details_id_seq RESTART WITH 1;

-- Reset webhook id sequence
ALTER SEQUENCE webhook_id_seq RESTART WITH 1;

-- Commit the transaction
COMMIT;

-- Note: This script ensures test isolation by completely clearing all data between test executions
-- while maintaining the database schema structure. This approach is more efficient than
-- recreating the entire schema for each test and ensures consistent test execution.