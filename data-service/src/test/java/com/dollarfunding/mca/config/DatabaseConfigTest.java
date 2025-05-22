package com.dollarfunding.mca.config;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.datasource.LazyConnectionDataSourceProxy;
import org.springframework.test.context.ActiveProfiles;

import javax.sql.DataSource;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for the DatabaseConfig class.
 * 
 * This test class verifies that the database configuration is correctly set up
 * and that the appropriate data sources are created based on the active profile.
 */
@SpringBootTest
@ActiveProfiles("test")
public class DatabaseConfigTest {

    @Autowired
    private DataSource dataSource;

    /**
     * Test that the data source is correctly configured.
     */
    @Test
    public void testDataSourceConfiguration() {
        assertNotNull(dataSource, "Data source should not be null");
        assertTrue(dataSource instanceof LazyConnectionDataSourceProxy, 
                "Data source should be a LazyConnectionDataSourceProxy");
    }

    /**
     * Test that the operation type enum works correctly.
     */
    @Test
    public void testOperationTypeEnum() {
        // Test default operation type
        DatabaseConfig.OperationType defaultType = DatabaseConfig.getCurrentOperation();
        assertNotNull(defaultType, "Default operation type should not be null");
        
        // Test setting operation type to READ
        DatabaseConfig.setCurrentOperation(DatabaseConfig.OperationType.READ);
        DatabaseConfig.OperationType readType = DatabaseConfig.getCurrentOperation();
        assertNotNull(readType, "Read operation type should not be null");
        assertTrue(readType == DatabaseConfig.OperationType.READ, 
                "Operation type should be READ");
        
        // Test setting operation type to WRITE
        DatabaseConfig.setCurrentOperation(DatabaseConfig.OperationType.WRITE);
        DatabaseConfig.OperationType writeType = DatabaseConfig.getCurrentOperation();
        assertNotNull(writeType, "Write operation type should not be null");
        assertTrue(writeType == DatabaseConfig.OperationType.WRITE, 
                "Operation type should be WRITE");
        
        // Test clearing operation type
        DatabaseConfig.clearCurrentOperation();
        DatabaseConfig.OperationType clearedType = DatabaseConfig.getCurrentOperation();
        assertNotNull(clearedType, "Cleared operation type should not be null");
        assertTrue(clearedType == DatabaseConfig.OperationType.WRITE, 
                "Cleared operation type should default to WRITE");
    }
}