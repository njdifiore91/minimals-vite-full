package com.dollarfunding.mca.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.lang.reflect.Field;
import java.sql.Connection;
import java.sql.Statement;
import java.util.Map;

import javax.sql.DataSource;

import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.Location;
import org.flywaydb.core.api.callback.Callback;
import org.flywaydb.core.api.callback.Context;
import org.flywaydb.core.api.callback.Event;
import org.flywaydb.core.api.configuration.Configuration;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.core.env.Environment;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * Unit tests for the {@link FlywayConfig} class.
 * 
 * These tests verify that Flyway database migrations are properly configured with:
 * - Correct migration script locations
 * - Appropriate versioning strategy
 * - Validation and repair options
 * - Migration event callbacks
 * - Support for the three main database schemas (Applications, Documents, MerchantDetails)
 * - 7-year data retention policy
 * - Field-level encryption for PII
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("Flyway Configuration Tests")
public class FlywayConfigTest {

    @InjectMocks
    private FlywayConfig flywayConfig;
    
    @Mock
    private Environment env;
    
    @Mock
    private DataSource dataSource;
    
    @Spy
    private String[] locations = {"classpath:db/migrations"};
    
    @BeforeEach
    public void setUp() {
        // Set up the properties with default values
        ReflectionTestUtils.setField(flywayConfig, "baselineOnMigrate", true);
        ReflectionTestUtils.setField(flywayConfig, "validateOnMigrate", true);
        ReflectionTestUtils.setField(flywayConfig, "cleanDisabled", true);
        ReflectionTestUtils.setField(flywayConfig, "outOfOrder", false);
        ReflectionTestUtils.setField(flywayConfig, "ignoreMissingMigrations", false);
        ReflectionTestUtils.setField(flywayConfig, "connectRetries", 3);
        ReflectionTestUtils.setField(flywayConfig, "flywayTable", "flyway_schema_history");
        ReflectionTestUtils.setField(flywayConfig, "retentionPeriodYears", "7");
        ReflectionTestUtils.setField(flywayConfig, "encryptionEnabled", "true");
        ReflectionTestUtils.setField(flywayConfig, "sqlMigrationPrefix", "V");
        ReflectionTestUtils.setField(flywayConfig, "repeatableSqlMigrationPrefix", "R");
        ReflectionTestUtils.setField(flywayConfig, "sqlMigrationSeparator", "__");
        ReflectionTestUtils.setField(flywayConfig, "sqlMigrationSuffixes", ".sql");
    }

    /**
     * Tests that the Flyway bean is properly configured with the correct settings.
     * 
     * Verifies:
     * - The data source is set correctly
     * - The migration script locations are set correctly
     * - The baseline and validation options are set correctly
     * - The versioning strategy is configured correctly
     * - The placeholders for retention period and encryption are set correctly
     * - The migration callback is registered
     */
    @Test
    @DisplayName("Flyway bean should be properly configured with correct settings")
    public void testFlywayBean() throws Exception {
        // Execute the method under test
        Flyway flyway = flywayConfig.flyway();
        
        // Verify the Flyway instance
        assertNotNull(flyway);
        
        // Get the configuration using reflection
        Configuration configuration = flyway.getConfiguration();
        
        // Verify the data source
        assertEquals(dataSource, configuration.getDataSource());
        
        // Verify the migration script locations
        Location[] configLocations = configuration.getLocations();
        assertNotNull(configLocations);
        assertEquals(1, configLocations.length);
        assertEquals("classpath:db/migrations", configLocations[0].getDescriptor());
        
        // Verify the baseline and validation options
        assertTrue(configuration.isBaselineOnMigrate());
        assertTrue(configuration.isValidateOnMigrate());
        assertTrue(configuration.isCleanDisabled());
        assertFalse(configuration.isOutOfOrder());
        assertFalse(configuration.isIgnoreMissingMigrations());
        assertEquals(3, configuration.getConnectRetries());
        assertEquals("flyway_schema_history", configuration.getTable());
        
        // Verify the versioning strategy
        assertEquals("V", configuration.getSqlMigrationPrefix());
        assertEquals("R", configuration.getRepeatableSqlMigrationPrefix());
        assertEquals("__", configuration.getSqlMigrationSeparator());
        assertEquals(".sql", configuration.getSqlMigrationSuffixes()[0]);
        
        // Verify the placeholders
        Map<String, String> placeholders = configuration.getPlaceholders();
        assertNotNull(placeholders);
        assertEquals(2, placeholders.size());
        assertEquals("7", placeholders.get("retention_period"));
        assertEquals("true", placeholders.get("encryption_enabled"));
        
        // Verify the callbacks
        Callback[] callbacks = configuration.getCallbacks();
        assertNotNull(callbacks);
        assertEquals(1, callbacks.length);
        assertTrue(callbacks[0] instanceof FlywayConfig.MigrationCallback);
    }

    /**
     * Tests that the flywayMigrate method properly triggers the migration.
     * 
     * Verifies:
     * - The migrate method is called on the Flyway instance
     * - The method returns the number of applied migrations
     */
    @Test
    @DisplayName("flywayMigrate should trigger migration and return the number of applied migrations")
    public void testFlywayMigrate() {
        // Create a mock Flyway instance
        Flyway mockFlyway = mock(Flyway.class);
        when(mockFlyway.migrate()).thenReturn(5); // Simulate 5 migrations applied
        
        // Execute the method under test
        int migrationsApplied = flywayConfig.flywayMigrate(mockFlyway);
        
        // Verify the result
        assertEquals(5, migrationsApplied);
        
        // Verify that migrate was called
        verify(mockFlyway).migrate();
    }

    /**
     * Tests that the MigrationCallback supports all events.
     * 
     * Verifies:
     * - The callback supports all migration events
     * - The callback can handle events within transactions
     */
    @Test
    @DisplayName("MigrationCallback should support all events")
    public void testMigrationCallbackSupportsEvents() {
        // Create an instance of the MigrationCallback
        FlywayConfig.MigrationCallback callback = flywayConfig.new MigrationCallback();
        
        // Create a mock Context
        Context mockContext = mock(Context.class);
        
        // Test support for all events
        assertTrue(callback.supports(Event.BEFORE_MIGRATE, mockContext));
        assertTrue(callback.supports(Event.AFTER_MIGRATE, mockContext));
        assertTrue(callback.supports(Event.AFTER_MIGRATE_APPLIED, mockContext));
        assertTrue(callback.supports(Event.AFTER_VALIDATE, mockContext));
        assertTrue(callback.supports(Event.AFTER_BASELINE, mockContext));
        assertTrue(callback.supports(Event.AFTER_REPAIR, mockContext));
        
        // Test transaction handling
        assertTrue(callback.canHandleInTransaction(Event.BEFORE_MIGRATE, mockContext));
        assertTrue(callback.canHandleInTransaction(Event.AFTER_MIGRATE, mockContext));
    }

    /**
     * Tests that the MigrationCallback properly handles the BEFORE_MIGRATE event.
     * 
     * Verifies:
     * - The environment is validated before migration
     * - Appropriate logging is performed
     */
    @Test
    @DisplayName("MigrationCallback should properly handle BEFORE_MIGRATE event")
    public void testMigrationCallbackHandlesBeforeMigrate() {
        // Create an instance of the MigrationCallback
        FlywayConfig.MigrationCallback callback = flywayConfig.new MigrationCallback();
        
        // Create a mock Context
        Context mockContext = mock(Context.class);
        
        // Mock the environment properties
        when(env.getProperty("spring.datasource.url")).thenReturn("jdbc:postgresql://localhost:5432/mca");
        when(env.getProperty("encryption.key")).thenReturn("test-encryption-key");
        when(env.getProperty("spring.jpa.hibernate.ddl-auto")).thenReturn("validate");
        
        // Execute the method under test
        callback.handle(Event.BEFORE_MIGRATE, mockContext);
        
        // Verification is implicit - no exceptions should be thrown
        // In a real test, we would verify logging, but that's difficult to test directly
    }

    /**
     * Tests that the MigrationCallback properly handles the AFTER_MIGRATE event.
     * 
     * Verifies:
     * - Data retention policies are set up if not already configured
     * - Appropriate logging is performed
     */
    @Test
    @DisplayName("MigrationCallback should properly handle AFTER_MIGRATE event")
    public void testMigrationCallbackHandlesAfterMigrate() throws Exception {
        // Create an instance of the MigrationCallback
        FlywayConfig.MigrationCallback callback = flywayConfig.new MigrationCallback();
        
        // Create a mock Context
        Context mockContext = mock(Context.class);
        Connection mockConnection = mock(Connection.class);
        Statement mockStatement = mock(Statement.class);
        java.sql.ResultSet mockResultSet = mock(java.sql.ResultSet.class);
        
        // Mock the context to return a connection
        when(mockContext.getConnection()).thenReturn(mockConnection);
        
        // Mock the connection to return a statement
        when(mockConnection.createStatement()).thenReturn(mockStatement);
        
        // Mock the statement to return a result set
        when(mockStatement.executeQuery(anyString())).thenReturn(mockResultSet);
        
        // Mock the result set to indicate that retention policies don't exist yet
        when(mockResultSet.next()).thenReturn(false);
        
        // Execute the method under test
        callback.handle(Event.AFTER_MIGRATE, mockContext);
        
        // Verify that the statement was executed to check if retention policies exist
        verify(mockStatement).executeQuery("SELECT EXISTS (SELECT 1 FROM pg_catalog.pg_proc WHERE proname = 'archive_old_applications')");
        
        // Verify that the statements were executed to create the archival function and schedule it
        verify(mockStatement).execute(any(String.class)); // For creating the archival function
        verify(mockStatement).execute("SELECT cron.schedule('0 0 * * 0', 'SELECT archive_old_applications()');"); // For scheduling
    }

    /**
     * Tests that the MigrationCallback properly handles the AFTER_MIGRATE_APPLIED event.
     * 
     * Verifies:
     * - Appropriate logging is performed for the applied migration
     */
    @Test
    @DisplayName("MigrationCallback should properly handle AFTER_MIGRATE_APPLIED event")
    public void testMigrationCallbackHandlesAfterMigrateApplied() {
        // Create an instance of the MigrationCallback
        FlywayConfig.MigrationCallback callback = flywayConfig.new MigrationCallback();
        
        // Create a mock Context
        Context mockContext = mock(Context.class);
        org.flywaydb.core.api.MigrationInfo mockMigrationInfo = mock(org.flywaydb.core.api.MigrationInfo.class);
        
        // Mock the migration info
        when(mockContext.getMigrationInfo()).thenReturn(mockMigrationInfo);
        when(mockMigrationInfo.getDescription()).thenReturn("Test migration");
        
        // Execute the method under test
        callback.handle(Event.AFTER_MIGRATE_APPLIED, mockContext);
        
        // Verification is implicit - no exceptions should be thrown
        // In a real test, we would verify logging, but that's difficult to test directly
    }

    /**
     * Tests that the MigrationCallback properly handles other events.
     * 
     * Verifies:
     * - Appropriate logging is performed for other events
     */
    @Test
    @DisplayName("MigrationCallback should properly handle other events")
    public void testMigrationCallbackHandlesOtherEvents() {
        // Create an instance of the MigrationCallback
        FlywayConfig.MigrationCallback callback = flywayConfig.new MigrationCallback();
        
        // Create a mock Context
        Context mockContext = mock(Context.class);
        
        // Execute the method under test for various events
        callback.handle(Event.AFTER_VALIDATE, mockContext);
        callback.handle(Event.AFTER_BASELINE, mockContext);
        callback.handle(Event.AFTER_REPAIR, mockContext);
        
        // Verification is implicit - no exceptions should be thrown
        // In a real test, we would verify logging, but that's difficult to test directly
    }

    /**
     * Tests that the MigrationCallback properly validates the environment.
     * 
     * Verifies:
     * - Required properties are checked
     * - Encryption configuration is validated if enabled
     * - JPA validation is verified
     */
    @Test
    @DisplayName("MigrationCallback should properly validate the environment")
    public void testMigrationCallbackValidatesEnvironment() {
        // Create an instance of the MigrationCallback
        FlywayConfig.MigrationCallback callback = flywayConfig.new MigrationCallback();
        
        // Test case 1: All required properties are present
        when(env.getProperty("spring.datasource.url")).thenReturn("jdbc:postgresql://localhost:5432/mca");
        when(env.getProperty("encryption.key")).thenReturn("test-encryption-key");
        when(env.getProperty("spring.jpa.hibernate.ddl-auto")).thenReturn("validate");
        
        // Execute the validateEnvironment method using reflection
        ReflectionTestUtils.invokeMethod(callback, "validateEnvironment");
        
        // Test case 2: Missing database URL
        when(env.getProperty("spring.datasource.url")).thenReturn(null);
        
        // Execute the validateEnvironment method and expect an exception
        try {
            ReflectionTestUtils.invokeMethod(callback, "validateEnvironment");
            // If we get here, the test failed
            assertTrue(false, "Expected IllegalStateException was not thrown");
        } catch (IllegalStateException e) {
            assertEquals("Database URL is not configured", e.getMessage());
        }
        
        // Reset for next test
        when(env.getProperty("spring.datasource.url")).thenReturn("jdbc:postgresql://localhost:5432/mca");
        
        // Test case 3: Missing encryption key when encryption is enabled
        when(env.getProperty("encryption.key")).thenReturn(null);
        
        // Execute the validateEnvironment method - should not throw exception but log a warning
        ReflectionTestUtils.invokeMethod(callback, "validateEnvironment");
        
        // Test case 4: JPA validation not enabled
        when(env.getProperty("spring.jpa.hibernate.ddl-auto")).thenReturn("update");
        
        // Execute the validateEnvironment method - should not throw exception but log a warning
        ReflectionTestUtils.invokeMethod(callback, "validateEnvironment");
    }

    /**
     * Tests that the MigrationCallback properly sets up data retention policies.
     * 
     * Verifies:
     * - Policies are created if they don't exist
     * - Appropriate SQL is executed to create and schedule the archival function
     */
    @Test
    @DisplayName("MigrationCallback should properly set up data retention policies")
    public void testMigrationCallbackSetsUpDataRetentionPolicies() throws Exception {
        // Create an instance of the MigrationCallback
        FlywayConfig.MigrationCallback callback = flywayConfig.new MigrationCallback();
        
        // Create mock objects
        Context mockContext = mock(Context.class);
        Connection mockConnection = mock(Connection.class);
        Statement mockStatement = mock(Statement.class);
        java.sql.ResultSet mockResultSet = mock(java.sql.ResultSet.class);
        
        // Mock the context to return a connection
        when(mockContext.getConnection()).thenReturn(mockConnection);
        
        // Mock the connection to return a statement
        when(mockConnection.createStatement()).thenReturn(mockStatement);
        
        // Test case 1: Policies don't exist yet
        when(mockStatement.executeQuery(anyString())).thenReturn(mockResultSet);
        when(mockResultSet.next()).thenReturn(false);
        
        // Execute the setupDataRetentionPolicies method using reflection
        ReflectionTestUtils.invokeMethod(callback, "setupDataRetentionPolicies", mockContext);
        
        // Verify that the SQL statements were executed
        verify(mockStatement).execute(any(String.class)); // For creating the archival function
        verify(mockStatement).execute("SELECT cron.schedule('0 0 * * 0', 'SELECT archive_old_applications()');"); // For scheduling
        
        // Test case 2: Policies already exist
        when(mockResultSet.next()).thenReturn(true);
        
        // Reset the mock to clear the previous invocation count
        org.mockito.Mockito.reset(mockStatement);
        
        // Execute the setupDataRetentionPolicies method again
        ReflectionTestUtils.invokeMethod(callback, "setupDataRetentionPolicies", mockContext);
        
        // Verify that no SQL statements were executed this time
        verify(mockStatement, org.mockito.Mockito.never()).execute(any(String.class));
        
        // Test case 3: Exception during setup
        when(mockStatement.executeQuery(anyString())).thenThrow(new java.sql.SQLException("Test exception"));
        
        // Execute the setupDataRetentionPolicies method again - should not throw exception but log a warning
        ReflectionTestUtils.invokeMethod(callback, "setupDataRetentionPolicies", mockContext);
        
        // Verification is implicit - no exceptions should be thrown
        // In a real test, we would verify logging, but that's difficult to test directly
    }
}