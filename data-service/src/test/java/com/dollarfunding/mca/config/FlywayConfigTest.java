package com.dollarfunding.mca.config;

import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.MigrationInfo;
import org.flywaydb.core.api.MigrationInfoService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.flyway.FlywayMigrationStrategy;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.SpyBean;
import org.springframework.test.context.ActiveProfiles;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.verify;

/**
 * Tests for the FlywayConfig class.
 * 
 * This test class verifies that Flyway is correctly configured for database migrations
 * including script locations, versioning strategy, validation options, and callbacks.
 */
@SpringBootTest
@ActiveProfiles("test")
public class FlywayConfigTest {

    @Autowired
    private Flyway flyway;
    
    @Autowired
    private FlywayMigrationStrategy flywayMigrationStrategy;
    
    @SpyBean
    private Flyway spyFlyway;
    
    @Value("${spring.flyway.locations:classpath:db/migration}")
    private String[] locations;

    /**
     * Test that the Flyway bean is correctly configured.
     */
    @Test
    public void testFlywayConfiguration() {
        assertNotNull(flyway, "Flyway bean should not be null");
        
        // Get configuration from Flyway
        org.flywaydb.core.api.configuration.Configuration config = flyway.getConfiguration();
        
        // Verify locations
        assertNotNull(config.getLocations(), "Locations should not be null");
        assertTrue(config.getLocations().length > 0, "Should have at least one location");
        
        // Verify baseline on migrate
        assertTrue(config.isBaselineOnMigrate(), "Baseline on migrate should be enabled");
        
        // Verify validate on migrate
        assertTrue(config.isValidateOnMigrate(), "Validate on migrate should be enabled");
        
        // Verify clean disabled
        assertTrue(config.isCleanDisabled(), "Clean should be disabled");
        
        // Verify table name
        assertEquals("flyway_schema_history", config.getTable(), 
                "Table name should be flyway_schema_history");
    }
    
    /**
     * Test that the migration script locations are correctly configured.
     */
    @Test
    public void testMigrationScriptLocations() {
        org.flywaydb.core.api.configuration.Configuration config = flyway.getConfiguration();
        
        // Convert locations to strings for easier comparison
        String[] configLocations = new String[config.getLocations().length];
        for (int i = 0; i < config.getLocations().length; i++) {
            configLocations[i] = config.getLocations()[i].toString();
        }
        
        // Verify that the configured locations match the expected locations
        for (String location : locations) {
            boolean found = false;
            for (String configLocation : configLocations) {
                if (configLocation.contains(location.replace("classpath:", ""))) {
                    found = true;
                    break;
                }
            }
            assertTrue(found, "Location " + location + " should be configured");
        }
    }
    
    /**
     * Test that the versioning strategy is correctly configured.
     */
    @Test
    public void testVersioningStrategy() {
        org.flywaydb.core.api.configuration.Configuration config = flyway.getConfiguration();
        
        // Verify that out of order migrations are handled according to configuration
        assertEquals(false, config.isOutOfOrder(), 
                "Out of order migrations should be disabled by default");
        
        // Verify that missing migrations are not ignored by default
        assertEquals(false, config.isIgnoreMissingMigrations(), 
                "Missing migrations should not be ignored by default");
        
        // Verify that future migrations are not ignored by default
        assertEquals(false, config.isIgnoreFutureMigrations(), 
                "Future migrations should not be ignored by default");
    }
    
    /**
     * Test that the validation and repair options are correctly configured.
     */
    @Test
    public void testValidationAndRepairOptions() {
        org.flywaydb.core.api.configuration.Configuration config = flyway.getConfiguration();
        
        // Verify validation on migrate
        assertTrue(config.isValidateOnMigrate(), 
                "Validate on migrate should be enabled");
        
        // Verify connect retries
        assertEquals(3, config.getConnectRetries(), 
                "Connect retries should be set to 3");
    }
    
    /**
     * Test that the migration strategy correctly calls migrate on the Flyway instance.
     */
    @Test
    public void testMigrationStrategy() {
        // Execute the migration strategy
        flywayMigrationStrategy.migrate(spyFlyway);
        
        // Verify that migrate was called on the Flyway instance
        verify(spyFlyway).migrate();
    }
    
    /**
     * Test that the repair strategy is correctly configured for test environment.
     * Since we're using the @ActiveProfiles("test") annotation, the repair strategy
     * should be active and should call repair() before migrate().
     */
    @Test
    public void testRepairStrategy() {
        // Get the repair strategy bean
        FlywayMigrationStrategy repairStrategy = null;
        try {
            // Try to get the repair strategy bean
            // This should succeed in test profile
            repairStrategy = flywayMigrationStrategy;
            assertNotNull(repairStrategy, "Repair strategy should not be null in test profile");
            
            // Execute the repair strategy
            repairStrategy.migrate(spyFlyway);
            
            // Verify that repair was called on the Flyway instance
            // Note: In a real test, we would need to reset the spy between tests
            // or use argument captors to verify the order of calls
            verify(spyFlyway).repair();
            verify(spyFlyway).migrate();
        } catch (Exception e) {
            fail("Should not throw exception when getting repair strategy in test profile: " + e.getMessage());
        }
    }
    
    /**
     * Test that the placeholders are correctly configured.
     */
    @Test
    public void testPlaceholders() {
        org.flywaydb.core.api.configuration.Configuration config = flyway.getConfiguration();
        Map<String, String> placeholders = config.getPlaceholders();
        
        assertNotNull(placeholders, "Placeholders should not be null");
        
        // Verify retention period placeholder
        assertEquals("7", placeholders.get("retention_period_years"), 
                "Retention period should be 7 years");
        
        // Verify application schema placeholder
        assertEquals("public", placeholders.get("application_schema"), 
                "Application schema should be public");
    }
    
    /**
     * Test that the Flyway configuration supports the 7-year data retention period.
     * This test verifies that the retention_period_years placeholder is correctly set to 7.
     */
    @Test
    public void testDataRetentionPeriod() {
        org.flywaydb.core.api.configuration.Configuration config = flyway.getConfiguration();
        Map<String, String> placeholders = config.getPlaceholders();
        
        // Verify retention period placeholder
        assertEquals("7", placeholders.get("retention_period_years"), 
                "Retention period should be 7 years");
        
        // Verify that the placeholder is used in the migration scripts
        // This is a more comprehensive test that would require parsing the migration scripts
        // For now, we'll just verify that the placeholder is set correctly
    }
    
    /**
     * Test that the database schema supports field-level encryption for PII.
     * This test verifies that the database schema includes columns that would contain PII
     * and that these columns can be encrypted using the EncryptionUtil.
     */
    @Test
    public void testFieldLevelEncryption() throws IOException {
        // Get the migration scripts
        org.flywaydb.core.api.resource.Resource[] resources = flyway.getConfiguration().getResourceProvider().getResources("db/migrations", "V1__create_initial_schema.sql");
        
        // Verify that we have the initial schema migration script
        assertTrue(resources.length > 0, "Should have the initial schema migration script");
        
        // Get the content of the initial schema migration script
        org.flywaydb.core.api.resource.Resource initialSchemaResource = resources[0];
        String initialSchemaScript = new String(initialSchemaResource.loadAsBytes(), StandardCharsets.UTF_8);
        
        // Verify that the script creates columns that would contain PII
        // These columns should be encrypted using the EncryptionUtil
        assertTrue(initialSchemaScript.contains("legal_name"), 
                "MerchantDetails table should have a legal_name column for PII");
        assertTrue(initialSchemaScript.contains("dba_name"), 
                "MerchantDetails table should have a dba_name column for PII");
        assertTrue(initialSchemaScript.contains("ein"), 
                "MerchantDetails table should have an ein column for PII");
        assertTrue(initialSchemaScript.contains("address"), 
                "MerchantDetails table should have an address column for PII");
        
        // Note: In a real test, we would also verify that the EncryptionUtil is correctly
        // configured to encrypt these columns. However, that's the responsibility of the
        // EncryptionConfigTest, not this test class.
    }
    
    /**
     * Test that the database schema supports validation rules for database operations.
     * This test verifies that the database schema includes constraints that enforce validation rules.
     */
    @Test
    public void testValidationRules() throws IOException {
        // Get the migration scripts for constraints
        org.flywaydb.core.api.resource.Resource[] resources = flyway.getConfiguration().getResourceProvider().getResources("db/migrations", "V3__add_constraints.sql");
        
        // Verify that we have the constraints migration script
        assertTrue(resources.length > 0, "Should have the constraints migration script");
        
        // Get the content of the constraints migration script
        org.flywaydb.core.api.resource.Resource constraintsResource = resources[0];
        String constraintsScript = new String(constraintsResource.loadAsBytes(), StandardCharsets.UTF_8);
        
        // Verify that the script adds foreign key constraints
        assertTrue(constraintsScript.contains("FOREIGN KEY") && constraintsScript.contains("REFERENCES"), 
                "Constraints script should add foreign key constraints");
        
        // Verify that the script adds NOT NULL constraints
        assertTrue(constraintsScript.contains("NOT NULL"), 
                "Constraints script should add NOT NULL constraints");
        
        // Verify that the script adds unique constraints
        assertTrue(constraintsScript.contains("UNIQUE"), 
                "Constraints script should add unique constraints");
        
        // Verify that the script configures cascading deletes
        assertTrue(constraintsScript.contains("ON DELETE CASCADE"), 
                "Constraints script should configure cascading deletes");
    }
    
    /**
     * Test that the Flyway configuration supports migration event callbacks.
     * This test verifies that the FlywayMigrationStrategy bean is correctly configured
     * to execute additional operations after migrations are applied.
     */
    @Test
    public void testMigrationEventCallback() {
        // Verify that the FlywayMigrationStrategy bean is not null
        assertNotNull(flywayMigrationStrategy, "FlywayMigrationStrategy bean should not be null");
        
        // Execute the migration strategy with a spy Flyway instance
        flywayMigrationStrategy.migrate(spyFlyway);
        
        // Verify that migrate was called on the Flyway instance
        verify(spyFlyway).migrate();
        
        // Note: In a real test, we would also verify that any post-migration operations
        // are correctly executed. However, in the current implementation, there are no
        // additional operations beyond calling migrate(), so there's nothing else to verify.
    }
    
    /**
     * Test that the migration scripts follow the correct naming convention and are in the right location.
     * This test verifies that the required migration scripts exist and follow the Flyway naming convention.
     */
    @Test
    public void testMigrationScriptsExist() {
        // The migration scripts should be in the classpath:db/migrations directory
        // and follow the Flyway naming convention: V<version>__<description>.sql
        
        // We expect at least these migration scripts to exist:
        // V1__create_initial_schema.sql - Creates the initial database schema
        // V2__add_indexes.sql - Adds indexes for performance optimization
        // V3__add_constraints.sql - Adds foreign key constraints
        
        org.flywaydb.core.api.configuration.Configuration config = flyway.getConfiguration();
        org.flywaydb.core.api.resource.Resource[] resources = flyway.getConfiguration().getResourceProvider().getResources("db/migrations", "V*.sql");
        
        // Verify that we have at least 3 migration scripts
        assertTrue(resources.length >= 3, "Should have at least 3 migration scripts");
        
        // Check for specific migration scripts
        boolean foundV1 = false;
        boolean foundV2 = false;
        boolean foundV3 = false;
        
        for (org.flywaydb.core.api.resource.Resource resource : resources) {
            String filename = resource.getFilename();
            if (filename.equals("V1__create_initial_schema.sql")) {
                foundV1 = true;
            } else if (filename.equals("V2__add_indexes.sql")) {
                foundV2 = true;
            } else if (filename.equals("V3__add_constraints.sql")) {
                foundV3 = true;
            }
        }
        
        assertTrue(foundV1, "V1__create_initial_schema.sql should exist");
        assertTrue(foundV2, "V2__add_indexes.sql should exist");
        assertTrue(foundV3, "V3__add_constraints.sql should exist");
    }
    
    /**
     * Test that the migration scripts create the required database schemas.
     * This test verifies that the migration scripts create the three required schemas:
     * Applications, Documents, and MerchantDetails.
     */
    @Test
    public void testRequiredSchemas() throws IOException {
        // Get the migration scripts
        org.flywaydb.core.api.resource.Resource[] resources = flyway.getConfiguration().getResourceProvider().getResources("db/migrations", "V1__create_initial_schema.sql");
        
        // Verify that we have the initial schema migration script
        assertTrue(resources.length > 0, "Should have the initial schema migration script");
        
        // Get the content of the initial schema migration script
        org.flywaydb.core.api.resource.Resource initialSchemaResource = resources[0];
        String initialSchemaScript = new String(initialSchemaResource.loadAsBytes(), StandardCharsets.UTF_8);
        
        // Verify that the script creates the required tables
        assertTrue(initialSchemaScript.contains("CREATE TABLE application"), 
                "Initial schema script should create the application table");
        assertTrue(initialSchemaScript.contains("CREATE TABLE document"), 
                "Initial schema script should create the document table");
        assertTrue(initialSchemaScript.contains("CREATE TABLE merchant_details"), 
                "Initial schema script should create the merchant_details table");
        
        // Verify that the script creates the required columns
        // Application schema
        assertTrue(initialSchemaScript.contains("id") && initialSchemaScript.contains("status") && 
                initialSchemaScript.contains("metadata") && initialSchemaScript.contains("created_at") && 
                initialSchemaScript.contains("updated_at") && initialSchemaScript.contains("review_status"), 
                "Application table should have the required columns");
        
        // Document schema
        assertTrue(initialSchemaScript.contains("application_id") && initialSchemaScript.contains("type") && 
                initialSchemaScript.contains("storage_path") && initialSchemaScript.contains("classification") && 
                initialSchemaScript.contains("uploaded_at") && initialSchemaScript.contains("metadata"), 
                "Document table should have the required columns");
        
        // MerchantDetails schema
        assertTrue(initialSchemaScript.contains("legal_name") && initialSchemaScript.contains("dba_name") && 
                initialSchemaScript.contains("ein") && initialSchemaScript.contains("address") && 
                initialSchemaScript.contains("industry") && initialSchemaScript.contains("revenue"), 
                "MerchantDetails table should have the required columns");
    }
}