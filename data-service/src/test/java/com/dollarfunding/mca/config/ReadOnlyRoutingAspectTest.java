package com.dollarfunding.mca.config;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.stereotype.Service;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Tests for the ReadOnlyRoutingAspect class.
 * 
 * This test class verifies that the read-only routing aspect correctly routes
 * read-only operations to read replicas and write operations to the primary database.
 */
@SpringBootTest
@ActiveProfiles("test")
public class ReadOnlyRoutingAspectTest {

    @Autowired
    private TestService testService;

    /**
     * Test that read-only operations are routed to read replicas.
     */
    @Test
    public void testReadOnlyOperationsAreRoutedToReadReplicas() {
        // Execute a read-only operation
        DatabaseConfig.OperationType readType = testService.readOnlyOperation();
        
        // Verify that the operation type was set to READ
        assertEquals(DatabaseConfig.OperationType.READ, readType, 
                "Read-only operations should be routed to read replicas");
        
        // Verify that the operation type was reset after the operation
        assertEquals(DatabaseConfig.OperationType.WRITE, DatabaseConfig.getCurrentOperation(), 
                "Operation type should be reset after read-only operation");
    }

    /**
     * Test that write operations are routed to the primary database.
     */
    @Test
    public void testWriteOperationsAreRoutedToPrimaryDatabase() {
        // Execute a write operation
        DatabaseConfig.OperationType writeType = testService.writeOperation();
        
        // Verify that the operation type was set to WRITE
        assertEquals(DatabaseConfig.OperationType.WRITE, writeType, 
                "Write operations should be routed to the primary database");
        
        // Verify that the operation type was reset after the operation
        assertEquals(DatabaseConfig.OperationType.WRITE, DatabaseConfig.getCurrentOperation(), 
                "Operation type should be reset after write operation");
    }

    /**
     * Test service for testing the read-only routing aspect.
     */
    @Service
    public static class TestService {

        /**
         * Read-only operation that should be routed to read replicas.
         * 
         * @return The operation type during execution
         */
        @Transactional(readOnly = true)
        public DatabaseConfig.OperationType readOnlyOperation() {
            return DatabaseConfig.getCurrentOperation();
        }

        /**
         * Write operation that should be routed to the primary database.
         * 
         * @return The operation type during execution
         */
        @Transactional
        public DatabaseConfig.OperationType writeOperation() {
            return DatabaseConfig.getCurrentOperation();
        }
    }
}