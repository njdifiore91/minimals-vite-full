package com.dollarfunding.mca.util;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.MockedStatic;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.MDC;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.http.HttpHeaders;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Supplier;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

/**
 * Unit tests for the TraceUtil class.
 * 
 * Tests the generation, retrieval, setting, and propagation of correlation IDs
 * across different contexts including HTTP headers, RabbitMQ messages, and MDC logging.
 */
@ExtendWith(MockitoExtension.class)
public class TraceUtilTest {

    @Mock
    private HttpServletRequest mockRequest;

    @Mock
    private HttpServletResponse mockResponse;

    @Mock
    private Message mockMessage;

    @Mock
    private MessageProperties mockMessageProperties;

    private static final String TEST_CORRELATION_ID = "test-correlation-id-12345";
    private static final String GENERATED_CORRELATION_ID = "generated-correlation-id-67890";

    /**
     * Setup before each test.
     * Clears the MDC context to ensure a clean state for each test.
     */
    @BeforeEach
    public void setUp() {
        MDC.clear();
    }

    /**
     * Cleanup after each test.
     * Ensures the MDC context is cleared to prevent test interference.
     */
    @AfterEach
    public void tearDown() {
        MDC.clear();
    }

    /**
     * Tests that generateCorrelationId() returns a non-null, non-empty UUID string.
     */
    @Test
    public void testGenerateCorrelationId() {
        String correlationId = TraceUtil.generateCorrelationId();
        
        assertNotNull(correlationId, "Generated correlation ID should not be null");
        assertFalse(correlationId.isEmpty(), "Generated correlation ID should not be empty");
        
        // Verify it's a valid UUID
        UUID uuid = UUID.fromString(correlationId);
        assertNotNull(uuid, "Generated correlation ID should be a valid UUID");
    }

    /**
     * Tests that generateCorrelationId() returns unique values on consecutive calls.
     */
    @Test
    public void testGenerateCorrelationIdUniqueness() {
        String correlationId1 = TraceUtil.generateCorrelationId();
        String correlationId2 = TraceUtil.generateCorrelationId();
        
        assertNotEquals(correlationId1, correlationId2, "Consecutive correlation IDs should be unique");
    }

    /**
     * Tests that getCurrentCorrelationId() returns null when no correlation ID is set.
     */
    @Test
    public void testGetCurrentCorrelationIdWhenNotSet() {
        String correlationId = TraceUtil.getCurrentCorrelationId();
        
        assertNull(correlationId, "Current correlation ID should be null when not set");
    }

    /**
     * Tests that setCurrentCorrelationId() correctly sets the correlation ID in the MDC context
     * and getCurrentCorrelationId() correctly retrieves it.
     */
    @Test
    public void testSetAndGetCurrentCorrelationId() {
        TraceUtil.setCurrentCorrelationId(TEST_CORRELATION_ID);
        
        String retrievedCorrelationId = TraceUtil.getCurrentCorrelationId();
        
        assertEquals(TEST_CORRELATION_ID, retrievedCorrelationId, 
                "Retrieved correlation ID should match the one that was set");
    }

    /**
     * Tests that setCurrentCorrelationId() generates a new correlation ID when null is provided.
     */
    @Test
    public void testSetCurrentCorrelationIdWithNull() {
        try (MockedStatic<UUID> mockedUUID = Mockito.mockStatic(UUID.class)) {
            UUID mockUUID = mock(UUID.class);
            when(mockUUID.toString()).thenReturn(GENERATED_CORRELATION_ID);
            mockedUUID.when(UUID::randomUUID).thenReturn(mockUUID);
            
            String correlationId = TraceUtil.setCurrentCorrelationId(null);
            
            assertEquals(GENERATED_CORRELATION_ID, correlationId, 
                    "A new correlation ID should be generated when null is provided");
            assertEquals(GENERATED_CORRELATION_ID, TraceUtil.getCurrentCorrelationId(), 
                    "The generated correlation ID should be set in the MDC context");
        }
    }

    /**
     * Tests that setCurrentCorrelationId() generates a new correlation ID when an empty string is provided.
     */
    @Test
    public void testSetCurrentCorrelationIdWithEmptyString() {
        try (MockedStatic<UUID> mockedUUID = Mockito.mockStatic(UUID.class)) {
            UUID mockUUID = mock(UUID.class);
            when(mockUUID.toString()).thenReturn(GENERATED_CORRELATION_ID);
            mockedUUID.when(UUID::randomUUID).thenReturn(mockUUID);
            
            String correlationId = TraceUtil.setCurrentCorrelationId("");
            
            assertEquals(GENERATED_CORRELATION_ID, correlationId, 
                    "A new correlation ID should be generated when an empty string is provided");
            assertEquals(GENERATED_CORRELATION_ID, TraceUtil.getCurrentCorrelationId(), 
                    "The generated correlation ID should be set in the MDC context");
        }
    }

    /**
     * Tests that clearCurrentCorrelationId() correctly removes the correlation ID from the MDC context.
     */
    @Test
    public void testClearCurrentCorrelationId() {
        // Set a correlation ID
        TraceUtil.setCurrentCorrelationId(TEST_CORRELATION_ID);
        
        // Verify it was set
        assertEquals(TEST_CORRELATION_ID, TraceUtil.getCurrentCorrelationId(), 
                "Correlation ID should be set before clearing");
        
        // Clear it
        TraceUtil.clearCurrentCorrelationId();
        
        // Verify it was cleared
        assertNull(TraceUtil.getCurrentCorrelationId(), 
                "Correlation ID should be null after clearing");
    }

    /**
     * Tests that withCorrelationId(String, Supplier) correctly sets the correlation ID during execution
     * and restores the previous correlation ID afterward.
     */
    @Test
    public void testWithCorrelationIdSupplier() {
        // Set an initial correlation ID
        TraceUtil.setCurrentCorrelationId("initial-correlation-id");
        
        // Execute code with a different correlation ID
        String result = TraceUtil.withCorrelationId(TEST_CORRELATION_ID, () -> {
            // Verify the correlation ID is set correctly during execution
            assertEquals(TEST_CORRELATION_ID, TraceUtil.getCurrentCorrelationId(), 
                    "Correlation ID should be set to the specified value during execution");
            return "result";
        });
        
        // Verify the result is correct
        assertEquals("result", result, "The supplier should return the correct result");
        
        // Verify the original correlation ID is restored
        assertEquals("initial-correlation-id", TraceUtil.getCurrentCorrelationId(), 
                "Original correlation ID should be restored after execution");
    }

    /**
     * Tests that withCorrelationId(String, Supplier) correctly handles the case where no previous correlation ID was set.
     */
    @Test
    public void testWithCorrelationIdSupplierNoPreviousId() {
        // Ensure no correlation ID is set
        MDC.clear();
        
        // Execute code with a correlation ID
        String result = TraceUtil.withCorrelationId(TEST_CORRELATION_ID, () -> {
            // Verify the correlation ID is set correctly during execution
            assertEquals(TEST_CORRELATION_ID, TraceUtil.getCurrentCorrelationId(), 
                    "Correlation ID should be set to the specified value during execution");
            return "result";
        });
        
        // Verify the result is correct
        assertEquals("result", result, "The supplier should return the correct result");
        
        // Verify the correlation ID is cleared afterward
        assertNull(TraceUtil.getCurrentCorrelationId(), 
                "Correlation ID should be cleared after execution when no previous ID was set");
    }

    /**
     * Tests that withCorrelationId(String, Runnable) correctly sets the correlation ID during execution
     * and restores the previous correlation ID afterward.
     */
    @Test
    public void testWithCorrelationIdRunnable() {
        // Set an initial correlation ID
        TraceUtil.setCurrentCorrelationId("initial-correlation-id");
        
        // Use an AtomicReference to verify the correlation ID inside the runnable
        AtomicReference<String> capturedCorrelationId = new AtomicReference<>();
        
        // Execute code with a different correlation ID
        TraceUtil.withCorrelationId(TEST_CORRELATION_ID, () -> {
            capturedCorrelationId.set(TraceUtil.getCurrentCorrelationId());
        });
        
        // Verify the correlation ID was set correctly during execution
        assertEquals(TEST_CORRELATION_ID, capturedCorrelationId.get(), 
                "Correlation ID should be set to the specified value during execution");
        
        // Verify the original correlation ID is restored
        assertEquals("initial-correlation-id", TraceUtil.getCurrentCorrelationId(), 
                "Original correlation ID should be restored after execution");
    }

    /**
     * Tests that withCorrelationId(String, Runnable) correctly handles the case where no previous correlation ID was set.
     */
    @Test
    public void testWithCorrelationIdRunnableNoPreviousId() {
        // Ensure no correlation ID is set
        MDC.clear();
        
        // Use an AtomicReference to verify the correlation ID inside the runnable
        AtomicReference<String> capturedCorrelationId = new AtomicReference<>();
        
        // Execute code with a correlation ID
        TraceUtil.withCorrelationId(TEST_CORRELATION_ID, () -> {
            capturedCorrelationId.set(TraceUtil.getCurrentCorrelationId());
        });
        
        // Verify the correlation ID was set correctly during execution
        assertEquals(TEST_CORRELATION_ID, capturedCorrelationId.get(), 
                "Correlation ID should be set to the specified value during execution");
        
        // Verify the correlation ID is cleared afterward
        assertNull(TraceUtil.getCurrentCorrelationId(), 
                "Correlation ID should be cleared after execution when no previous ID was set");
    }

    /**
     * Tests that extractCorrelationIdFromHttpHeaders() correctly extracts the correlation ID from HTTP headers.
     */
    @Test
    public void testExtractCorrelationIdFromHttpHeaders() {
        // Create HTTP headers with a correlation ID
        HttpHeaders headers = new HttpHeaders();
        headers.set(TraceUtil.CORRELATION_ID_HEADER, TEST_CORRELATION_ID);
        
        // Extract the correlation ID
        String extractedCorrelationId = TraceUtil.extractCorrelationIdFromHttpHeaders(headers);
        
        // Verify the extracted correlation ID
        assertEquals(TEST_CORRELATION_ID, extractedCorrelationId, 
                "Extracted correlation ID should match the one in the headers");
    }

    /**
     * Tests that extractCorrelationIdFromHttpHeaders() returns null when the correlation ID is not present in the headers.
     */
    @Test
    public void testExtractCorrelationIdFromHttpHeadersWhenNotPresent() {
        // Create HTTP headers without a correlation ID
        HttpHeaders headers = new HttpHeaders();
        
        // Extract the correlation ID
        String extractedCorrelationId = TraceUtil.extractCorrelationIdFromHttpHeaders(headers);
        
        // Verify the extracted correlation ID is null
        assertNull(extractedCorrelationId, 
                "Extracted correlation ID should be null when not present in headers");
    }

    /**
     * Tests that extractCorrelationIdFromHttpHeaders() returns null when the headers are null.
     */
    @Test
    public void testExtractCorrelationIdFromHttpHeadersWithNullHeaders() {
        // Extract the correlation ID from null headers
        String extractedCorrelationId = TraceUtil.extractCorrelationIdFromHttpHeaders(null);
        
        // Verify the extracted correlation ID is null
        assertNull(extractedCorrelationId, 
                "Extracted correlation ID should be null when headers are null");
    }

    /**
     * Tests that extractCorrelationIdFromRequest() correctly extracts the correlation ID from an HTTP request.
     */
    @Test
    public void testExtractCorrelationIdFromRequest() {
        // Configure the mock request to return a correlation ID
        when(mockRequest.getHeader(TraceUtil.CORRELATION_ID_HEADER)).thenReturn(TEST_CORRELATION_ID);
        
        // Extract the correlation ID
        String extractedCorrelationId = TraceUtil.extractCorrelationIdFromRequest(mockRequest);
        
        // Verify the extracted correlation ID
        assertEquals(TEST_CORRELATION_ID, extractedCorrelationId, 
                "Extracted correlation ID should match the one in the request");
    }

    /**
     * Tests that extractCorrelationIdFromRequest() returns null when the correlation ID is not present in the request.
     */
    @Test
    public void testExtractCorrelationIdFromRequestWhenNotPresent() {
        // Configure the mock request to return null for the correlation ID header
        when(mockRequest.getHeader(TraceUtil.CORRELATION_ID_HEADER)).thenReturn(null);
        
        // Extract the correlation ID
        String extractedCorrelationId = TraceUtil.extractCorrelationIdFromRequest(mockRequest);
        
        // Verify the extracted correlation ID is null
        assertNull(extractedCorrelationId, 
                "Extracted correlation ID should be null when not present in request");
    }

    /**
     * Tests that extractCorrelationIdFromRequest() returns null when the request is null.
     */
    @Test
    public void testExtractCorrelationIdFromRequestWithNullRequest() {
        // Extract the correlation ID from a null request
        String extractedCorrelationId = TraceUtil.extractCorrelationIdFromRequest(null);
        
        // Verify the extracted correlation ID is null
        assertNull(extractedCorrelationId, 
                "Extracted correlation ID should be null when request is null");
    }

    /**
     * Tests that addCorrelationIdToHttpHeaders() correctly adds the current correlation ID to HTTP headers.
     */
    @Test
    public void testAddCorrelationIdToHttpHeaders() {
        // Set a correlation ID
        TraceUtil.setCurrentCorrelationId(TEST_CORRELATION_ID);
        
        // Create HTTP headers
        HttpHeaders headers = new HttpHeaders();
        
        // Add the correlation ID to the headers
        String addedCorrelationId = TraceUtil.addCorrelationIdToHttpHeaders(headers);
        
        // Verify the added correlation ID
        assertEquals(TEST_CORRELATION_ID, addedCorrelationId, 
                "Added correlation ID should match the current one");
        assertEquals(TEST_CORRELATION_ID, headers.getFirst(TraceUtil.CORRELATION_ID_HEADER), 
                "Correlation ID should be added to the headers");
    }

    /**
     * Tests that addCorrelationIdToHttpHeaders() generates a new correlation ID when none is set.
     */
    @Test
    public void testAddCorrelationIdToHttpHeadersWhenNoneSet() {
        try (MockedStatic<UUID> mockedUUID = Mockito.mockStatic(UUID.class)) {
            UUID mockUUID = mock(UUID.class);
            when(mockUUID.toString()).thenReturn(GENERATED_CORRELATION_ID);
            mockedUUID.when(UUID::randomUUID).thenReturn(mockUUID);
            
            // Ensure no correlation ID is set
            MDC.clear();
            
            // Create HTTP headers
            HttpHeaders headers = new HttpHeaders();
            
            // Add the correlation ID to the headers
            String addedCorrelationId = TraceUtil.addCorrelationIdToHttpHeaders(headers);
            
            // Verify a new correlation ID was generated and added
            assertEquals(GENERATED_CORRELATION_ID, addedCorrelationId, 
                    "A new correlation ID should be generated when none is set");
            assertEquals(GENERATED_CORRELATION_ID, headers.getFirst(TraceUtil.CORRELATION_ID_HEADER), 
                    "Generated correlation ID should be added to the headers");
            assertEquals(GENERATED_CORRELATION_ID, TraceUtil.getCurrentCorrelationId(), 
                    "Generated correlation ID should be set in the MDC context");
        }
    }

    /**
     * Tests that addCorrelationIdToResponse() correctly adds the current correlation ID to an HTTP response.
     */
    @Test
    public void testAddCorrelationIdToResponse() {
        // Set a correlation ID
        TraceUtil.setCurrentCorrelationId(TEST_CORRELATION_ID);
        
        // Add the correlation ID to the response
        String addedCorrelationId = TraceUtil.addCorrelationIdToResponse(mockResponse);
        
        // Verify the added correlation ID
        assertEquals(TEST_CORRELATION_ID, addedCorrelationId, 
                "Added correlation ID should match the current one");
        
        // Verify the correlation ID was added to the response
        verify(mockResponse).setHeader(TraceUtil.CORRELATION_ID_HEADER, TEST_CORRELATION_ID);
    }

    /**
     * Tests that addCorrelationIdToResponse() generates a new correlation ID when none is set.
     */
    @Test
    public void testAddCorrelationIdToResponseWhenNoneSet() {
        try (MockedStatic<UUID> mockedUUID = Mockito.mockStatic(UUID.class)) {
            UUID mockUUID = mock(UUID.class);
            when(mockUUID.toString()).thenReturn(GENERATED_CORRELATION_ID);
            mockedUUID.when(UUID::randomUUID).thenReturn(mockUUID);
            
            // Ensure no correlation ID is set
            MDC.clear();
            
            // Add the correlation ID to the response
            String addedCorrelationId = TraceUtil.addCorrelationIdToResponse(mockResponse);
            
            // Verify a new correlation ID was generated and added
            assertEquals(GENERATED_CORRELATION_ID, addedCorrelationId, 
                    "A new correlation ID should be generated when none is set");
            
            // Verify the correlation ID was added to the response
            verify(mockResponse).setHeader(TraceUtil.CORRELATION_ID_HEADER, GENERATED_CORRELATION_ID);
            
            // Verify the generated correlation ID was set in the MDC context
            assertEquals(GENERATED_CORRELATION_ID, TraceUtil.getCurrentCorrelationId(), 
                    "Generated correlation ID should be set in the MDC context");
        }
    }

    /**
     * Tests that extractCorrelationIdFromRabbitMQMessage() correctly extracts the correlation ID from a RabbitMQ message.
     */
    @Test
    public void testExtractCorrelationIdFromRabbitMQMessage() {
        // Configure the mock message and properties
        Map<String, Object> headers = new HashMap<>();
        headers.put(TraceUtil.RABBITMQ_CORRELATION_ID_HEADER, TEST_CORRELATION_ID);
        
        when(mockMessage.getMessageProperties()).thenReturn(mockMessageProperties);
        when(mockMessageProperties.getHeaders()).thenReturn(headers);
        
        // Extract the correlation ID
        String extractedCorrelationId = TraceUtil.extractCorrelationIdFromRabbitMQMessage(mockMessage);
        
        // Verify the extracted correlation ID
        assertEquals(TEST_CORRELATION_ID, extractedCorrelationId, 
                "Extracted correlation ID should match the one in the message");
    }

    /**
     * Tests that extractCorrelationIdFromRabbitMQMessage() returns null when the correlation ID is not present in the message.
     */
    @Test
    public void testExtractCorrelationIdFromRabbitMQMessageWhenNotPresent() {
        // Configure the mock message and properties with empty headers
        Map<String, Object> headers = new HashMap<>();
        
        when(mockMessage.getMessageProperties()).thenReturn(mockMessageProperties);
        when(mockMessageProperties.getHeaders()).thenReturn(headers);
        
        // Extract the correlation ID
        String extractedCorrelationId = TraceUtil.extractCorrelationIdFromRabbitMQMessage(mockMessage);
        
        // Verify the extracted correlation ID is null
        assertNull(extractedCorrelationId, 
                "Extracted correlation ID should be null when not present in message");
    }

    /**
     * Tests that extractCorrelationIdFromRabbitMQMessage() returns null when the message is null.
     */
    @Test
    public void testExtractCorrelationIdFromRabbitMQMessageWithNullMessage() {
        // Extract the correlation ID from a null message
        String extractedCorrelationId = TraceUtil.extractCorrelationIdFromRabbitMQMessage(null);
        
        // Verify the extracted correlation ID is null
        assertNull(extractedCorrelationId, 
                "Extracted correlation ID should be null when message is null");
    }

    /**
     * Tests that addCorrelationIdToRabbitMQMessage() correctly adds the current correlation ID to RabbitMQ message properties.
     */
    @Test
    public void testAddCorrelationIdToRabbitMQMessage() {
        // Set a correlation ID
        TraceUtil.setCurrentCorrelationId(TEST_CORRELATION_ID);
        
        // Add the correlation ID to the message properties
        String addedCorrelationId = TraceUtil.addCorrelationIdToRabbitMQMessage(mockMessageProperties);
        
        // Verify the added correlation ID
        assertEquals(TEST_CORRELATION_ID, addedCorrelationId, 
                "Added correlation ID should match the current one");
        
        // Verify the correlation ID was added to the message properties
        verify(mockMessageProperties).setHeader(TraceUtil.RABBITMQ_CORRELATION_ID_HEADER, TEST_CORRELATION_ID);
    }

    /**
     * Tests that addCorrelationIdToRabbitMQMessage() generates a new correlation ID when none is set.
     */
    @Test
    public void testAddCorrelationIdToRabbitMQMessageWhenNoneSet() {
        try (MockedStatic<UUID> mockedUUID = Mockito.mockStatic(UUID.class)) {
            UUID mockUUID = mock(UUID.class);
            when(mockUUID.toString()).thenReturn(GENERATED_CORRELATION_ID);
            mockedUUID.when(UUID::randomUUID).thenReturn(mockUUID);
            
            // Ensure no correlation ID is set
            MDC.clear();
            
            // Add the correlation ID to the message properties
            String addedCorrelationId = TraceUtil.addCorrelationIdToRabbitMQMessage(mockMessageProperties);
            
            // Verify a new correlation ID was generated and added
            assertEquals(GENERATED_CORRELATION_ID, addedCorrelationId, 
                    "A new correlation ID should be generated when none is set");
            
            // Verify the correlation ID was added to the message properties
            verify(mockMessageProperties).setHeader(TraceUtil.RABBITMQ_CORRELATION_ID_HEADER, GENERATED_CORRELATION_ID);
            
            // Verify the generated correlation ID was set in the MDC context
            assertEquals(GENERATED_CORRELATION_ID, TraceUtil.getCurrentCorrelationId(), 
                    "Generated correlation ID should be set in the MDC context");
        }
    }

    /**
     * Tests that createLogMessageWithCorrelationId(String) correctly includes the current correlation ID in a log message.
     */
    @Test
    public void testCreateLogMessageWithCorrelationId() {
        // Set a correlation ID
        TraceUtil.setCurrentCorrelationId(TEST_CORRELATION_ID);
        
        // Create a log message with the correlation ID
        String logMessage = TraceUtil.createLogMessageWithCorrelationId("Test message");
        
        // Verify the log message includes the correlation ID
        String expectedMessage = String.format(TraceUtil.CORRELATION_ID_LOG_PREFIX + " %s", 
                TEST_CORRELATION_ID, "Test message");
        assertEquals(expectedMessage, logMessage, 
                "Log message should include the correlation ID");
    }

    /**
     * Tests that createLogMessageWithCorrelationId(String) returns the original message when no correlation ID is set.
     */
    @Test
    public void testCreateLogMessageWithCorrelationIdWhenNoneSet() {
        // Ensure no correlation ID is set
        MDC.clear();
        
        // Create a log message
        String logMessage = TraceUtil.createLogMessageWithCorrelationId("Test message");
        
        // Verify the log message is unchanged
        assertEquals("Test message", logMessage, 
                "Log message should be unchanged when no correlation ID is set");
    }

    /**
     * Tests that createLogMessageWithCorrelationId(String, String) correctly includes the specified correlation ID in a log message.
     */
    @Test
    public void testCreateLogMessageWithSpecifiedCorrelationId() {
        // Create a log message with a specified correlation ID
        String logMessage = TraceUtil.createLogMessageWithCorrelationId(TEST_CORRELATION_ID, "Test message");
        
        // Verify the log message includes the correlation ID
        String expectedMessage = String.format(TraceUtil.CORRELATION_ID_LOG_PREFIX + " %s", 
                TEST_CORRELATION_ID, "Test message");
        assertEquals(expectedMessage, logMessage, 
                "Log message should include the specified correlation ID");
    }

    /**
     * Tests that createLogMessageWithCorrelationId(String, String) returns the original message when the correlation ID is null.
     */
    @Test
    public void testCreateLogMessageWithSpecifiedCorrelationIdWhenNull() {
        // Create a log message with a null correlation ID
        String logMessage = TraceUtil.createLogMessageWithCorrelationId(null, "Test message");
        
        // Verify the log message is unchanged
        assertEquals("Test message", logMessage, 
                "Log message should be unchanged when correlation ID is null");
    }

    /**
     * Tests that initializeTracing(String) correctly sets the correlation ID and returns it.
     */
    @Test
    public void testInitializeTracing() {
        // Initialize tracing with a correlation ID
        String initializedCorrelationId = TraceUtil.initializeTracing(TEST_CORRELATION_ID);
        
        // Verify the correlation ID was set
        assertEquals(TEST_CORRELATION_ID, initializedCorrelationId, 
                "Initialized correlation ID should match the provided one");
        assertEquals(TEST_CORRELATION_ID, TraceUtil.getCurrentCorrelationId(), 
                "Correlation ID should be set in the MDC context");
    }

    /**
     * Tests that initializeTracing(String) generates a new correlation ID when null is provided.
     */
    @Test
    public void testInitializeTracingWithNull() {
        try (MockedStatic<UUID> mockedUUID = Mockito.mockStatic(UUID.class)) {
            UUID mockUUID = mock(UUID.class);
            when(mockUUID.toString()).thenReturn(GENERATED_CORRELATION_ID);
            mockedUUID.when(UUID::randomUUID).thenReturn(mockUUID);
            
            // Initialize tracing with a null correlation ID
            String initializedCorrelationId = TraceUtil.initializeTracing(null);
            
            // Verify a new correlation ID was generated
            assertEquals(GENERATED_CORRELATION_ID, initializedCorrelationId, 
                    "A new correlation ID should be generated when null is provided");
            assertEquals(GENERATED_CORRELATION_ID, TraceUtil.getCurrentCorrelationId(), 
                    "Generated correlation ID should be set in the MDC context");
        }
    }

    /**
     * Tests that initializeTracing(HttpServletRequest) correctly extracts and sets the correlation ID from the request.
     */
    @Test
    public void testInitializeTracingFromRequest() {
        // Configure the mock request to return a correlation ID
        when(mockRequest.getHeader(TraceUtil.CORRELATION_ID_HEADER)).thenReturn(TEST_CORRELATION_ID);
        
        // Initialize tracing from the request
        String initializedCorrelationId = TraceUtil.initializeTracing(mockRequest);
        
        // Verify the correlation ID was extracted and set
        assertEquals(TEST_CORRELATION_ID, initializedCorrelationId, 
                "Initialized correlation ID should match the one from the request");
        assertEquals(TEST_CORRELATION_ID, TraceUtil.getCurrentCorrelationId(), 
                "Correlation ID should be set in the MDC context");
    }

    /**
     * Tests that initializeTracing(HttpServletRequest) generates a new correlation ID when none is in the request.
     */
    @Test
    public void testInitializeTracingFromRequestWhenNonePresent() {
        try (MockedStatic<UUID> mockedUUID = Mockito.mockStatic(UUID.class)) {
            UUID mockUUID = mock(UUID.class);
            when(mockUUID.toString()).thenReturn(GENERATED_CORRELATION_ID);
            mockedUUID.when(UUID::randomUUID).thenReturn(mockUUID);
            
            // Configure the mock request to return null for the correlation ID header
            when(mockRequest.getHeader(TraceUtil.CORRELATION_ID_HEADER)).thenReturn(null);
            
            // Initialize tracing from the request
            String initializedCorrelationId = TraceUtil.initializeTracing(mockRequest);
            
            // Verify a new correlation ID was generated
            assertEquals(GENERATED_CORRELATION_ID, initializedCorrelationId, 
                    "A new correlation ID should be generated when none is in the request");
            assertEquals(GENERATED_CORRELATION_ID, TraceUtil.getCurrentCorrelationId(), 
                    "Generated correlation ID should be set in the MDC context");
        }
    }

    /**
     * Tests that finalizeTracing() correctly clears the correlation ID from the MDC context.
     */
    @Test
    public void testFinalizeTracing() {
        // Set a correlation ID
        TraceUtil.setCurrentCorrelationId(TEST_CORRELATION_ID);
        
        // Verify it was set
        assertEquals(TEST_CORRELATION_ID, TraceUtil.getCurrentCorrelationId(), 
                "Correlation ID should be set before finalizing");
        
        // Finalize tracing
        TraceUtil.finalizeTracing();
        
        // Verify the correlation ID was cleared
        assertNull(TraceUtil.getCurrentCorrelationId(), 
                "Correlation ID should be null after finalizing");
    }
}