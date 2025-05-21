package com.dollarfunding.mca.util;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.http.HttpHeaders;

import java.util.UUID;
import java.util.function.Supplier;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

/**
 * Utility class for distributed tracing and correlation ID management across microservices.
 * Provides methods for generating, retrieving, setting, and propagating correlation IDs
 * to enable request tracking across different services.
 * 
 * This utility supports tracing across HTTP requests and RabbitMQ messages, allowing
 * for end-to-end tracking of requests as they flow through the MCA application's
 * microservices architecture. It integrates with SLF4J's MDC for log correlation.
 *
 * Key features:
 * - Correlation ID generation and management
 * - HTTP header propagation for REST API calls
 * - RabbitMQ message property propagation for asynchronous messaging
 * - Integration with logging via MDC
 * - Support for executing code blocks with specific correlation IDs
 */
public class TraceUtil {

    private static final Logger logger = LoggerFactory.getLogger(TraceUtil.class);

    /**
     * The key used to store the correlation ID in the MDC context.
     */
    public static final String CORRELATION_ID_KEY = "correlationId";

    /**
     * The HTTP header name used for passing the correlation ID between services.
     */
    public static final String CORRELATION_ID_HEADER = "X-Correlation-ID";

    /**
     * The RabbitMQ message property key used for correlation ID.
     */
    public static final String RABBITMQ_CORRELATION_ID_HEADER = "correlationId";
    
    /**
     * The prefix used for log messages that include the correlation ID.
     */
    public static final String CORRELATION_ID_LOG_PREFIX = "[correlationId=%s]";

    /**
     * Generates a new unique correlation ID.
     * Uses UUID.randomUUID() to ensure global uniqueness.
     *
     * @return A new unique correlation ID as a string
     */
    public static String generateCorrelationId() {
        return UUID.randomUUID().toString();
    }

    /**
     * Retrieves the current correlation ID from the MDC context.
     * If no correlation ID is found, returns null.
     *
     * @return The current correlation ID or null if not set
     */
    public static String getCurrentCorrelationId() {
        return MDC.get(CORRELATION_ID_KEY);
    }

    /**
     * Sets the correlation ID in the current MDC context.
     * If the provided correlation ID is null or empty, a new one will be generated.
     *
     * @param correlationId The correlation ID to set
     * @return The correlation ID that was set (either the provided one or a newly generated one)
     */
    public static String setCurrentCorrelationId(String correlationId) {
        String idToUse = (correlationId == null || correlationId.isEmpty()) 
                ? generateCorrelationId() 
                : correlationId;
        
        MDC.put(CORRELATION_ID_KEY, idToUse);
        logger.debug("Set correlation ID: {}", idToUse);
        return idToUse;
    }

    /**
     * Clears the correlation ID from the current MDC context.
     * This should be called at the end of request processing to prevent
     * correlation ID leakage between requests.
     */
    public static void clearCurrentCorrelationId() {
        logger.debug("Clearing correlation ID: {}", getCurrentCorrelationId());
        MDC.remove(CORRELATION_ID_KEY);
    }

    /**
     * Executes the provided code with the specified correlation ID set in the MDC context.
     * The previous correlation ID (if any) is restored after execution.
     *
     * @param correlationId The correlation ID to use during execution
     * @param supplier      The code to execute (as a Supplier)
     * @param <T>           The return type of the supplier
     * @return The result of the supplier execution
     */
    public static <T> T withCorrelationId(String correlationId, Supplier<T> supplier) {
        String previousCorrelationId = getCurrentCorrelationId();
        try {
            setCurrentCorrelationId(correlationId);
            return supplier.get();
        } finally {
            if (previousCorrelationId != null) {
                setCurrentCorrelationId(previousCorrelationId);
            } else {
                clearCurrentCorrelationId();
            }
        }
    }

    /**
     * Executes the provided runnable with the specified correlation ID set in the MDC context.
     * The previous correlation ID (if any) is restored after execution.
     *
     * @param correlationId The correlation ID to use during execution
     * @param runnable      The code to execute (as a Runnable)
     */
    public static void withCorrelationId(String correlationId, Runnable runnable) {
        String previousCorrelationId = getCurrentCorrelationId();
        try {
            setCurrentCorrelationId(correlationId);
            runnable.run();
        } finally {
            if (previousCorrelationId != null) {
                setCurrentCorrelationId(previousCorrelationId);
            } else {
                clearCurrentCorrelationId();
            }
        }
    }

    /**
     * Extracts the correlation ID from HTTP headers.
     * If no correlation ID is found in the headers, returns null.
     *
     * @param headers The HTTP headers to extract the correlation ID from
     * @return The correlation ID from the headers or null if not found
     */
    public static String extractCorrelationIdFromHttpHeaders(HttpHeaders headers) {
        if (headers != null && headers.containsKey(CORRELATION_ID_HEADER)) {
            String correlationId = headers.getFirst(CORRELATION_ID_HEADER);
            logger.debug("Extracted correlation ID from HTTP headers: {}", correlationId);
            return correlationId;
        }
        return null;
    }
    
    /**
     * Extracts the correlation ID from an HTTP servlet request.
     * If no correlation ID is found in the request, returns null.
     *
     * @param request The HTTP servlet request to extract the correlation ID from
     * @return The correlation ID from the request or null if not found
     */
    public static String extractCorrelationIdFromRequest(HttpServletRequest request) {
        if (request != null) {
            String correlationId = request.getHeader(CORRELATION_ID_HEADER);
            if (correlationId != null && !correlationId.isEmpty()) {
                logger.debug("Extracted correlation ID from HTTP request: {}", correlationId);
                return correlationId;
            }
        }
        return null;
    }

    /**
     * Adds the current correlation ID to the provided HTTP headers.
     * If no current correlation ID exists, a new one is generated.
     *
     * @param headers The HTTP headers to add the correlation ID to
     * @return The correlation ID that was added to the headers
     */
    public static String addCorrelationIdToHttpHeaders(HttpHeaders headers) {
        String correlationId = getCurrentCorrelationId();
        if (correlationId == null || correlationId.isEmpty()) {
            correlationId = generateCorrelationId();
            setCurrentCorrelationId(correlationId);
        }
        
        headers.set(CORRELATION_ID_HEADER, correlationId);
        logger.debug("Added correlation ID to HTTP headers: {}", correlationId);
        return correlationId;
    }
    
    /**
     * Adds the current correlation ID to the provided HTTP servlet response.
     * If no current correlation ID exists, a new one is generated.
     *
     * @param response The HTTP servlet response to add the correlation ID to
     * @return The correlation ID that was added to the response
     */
    public static String addCorrelationIdToResponse(HttpServletResponse response) {
        String correlationId = getCurrentCorrelationId();
        if (correlationId == null || correlationId.isEmpty()) {
            correlationId = generateCorrelationId();
            setCurrentCorrelationId(correlationId);
        }
        
        response.setHeader(CORRELATION_ID_HEADER, correlationId);
        logger.debug("Added correlation ID to HTTP response: {}", correlationId);
        return correlationId;
    }

    /**
     * Extracts the correlation ID from a RabbitMQ message.
     * If no correlation ID is found in the message properties, returns null.
     *
     * @param message The RabbitMQ message to extract the correlation ID from
     * @return The correlation ID from the message or null if not found
     */
    public static String extractCorrelationIdFromRabbitMQMessage(Message message) {
        if (message != null && message.getMessageProperties() != null) {
            MessageProperties properties = message.getMessageProperties();
            Object correlationId = properties.getHeaders().get(RABBITMQ_CORRELATION_ID_HEADER);
            
            if (correlationId != null) {
                String correlationIdStr = correlationId.toString();
                logger.debug("Extracted correlation ID from RabbitMQ message: {}", correlationIdStr);
                return correlationIdStr;
            }
        }
        return null;
    }

    /**
     * Adds the current correlation ID to the provided RabbitMQ message properties.
     * If no current correlation ID exists, a new one is generated.
     *
     * @param properties The RabbitMQ message properties to add the correlation ID to
     * @return The correlation ID that was added to the message properties
     */
    public static String addCorrelationIdToRabbitMQMessage(MessageProperties properties) {
        String correlationId = getCurrentCorrelationId();
        if (correlationId == null || correlationId.isEmpty()) {
            correlationId = generateCorrelationId();
            setCurrentCorrelationId(correlationId);
        }
        
        properties.setHeader(RABBITMQ_CORRELATION_ID_HEADER, correlationId);
        logger.debug("Added correlation ID to RabbitMQ message: {}", correlationId);
        return correlationId;
    }

    /**
     * Creates a log message that includes the current correlation ID.
     * This is useful for manual logging when the MDC context is not automatically included.
     *
     * @param message The log message
     * @return The log message with the correlation ID prepended
     */
    public static String createLogMessageWithCorrelationId(String message) {
        String correlationId = getCurrentCorrelationId();
        if (correlationId == null || correlationId.isEmpty()) {
            return message;
        }
        return String.format(CORRELATION_ID_LOG_PREFIX + " %s", correlationId, message);
    }
    
    /**
     * Creates a log message that includes the specified correlation ID.
     * This is useful when you need to log with a specific correlation ID that may be
     * different from the one in the current context.
     *
     * @param correlationId The correlation ID to include in the log message
     * @param message The log message
     * @return The log message with the correlation ID prepended
     */
    public static String createLogMessageWithCorrelationId(String correlationId, String message) {
        if (correlationId == null || correlationId.isEmpty()) {
            return message;
        }
        return String.format(CORRELATION_ID_LOG_PREFIX + " %s", correlationId, message);
    }

    /**
     * Initializes tracing for a new request.
     * If a correlation ID is provided, it will be used; otherwise, a new one will be generated.
     * This method should be called at the beginning of request processing.
     *
     * @param correlationId The correlation ID to use (can be null)
     * @return The correlation ID that was set
     */
    public static String initializeTracing(String correlationId) {
        String idToUse = setCurrentCorrelationId(correlationId);
        logger.debug("Initialized tracing with correlation ID: {}", idToUse);
        return idToUse;
    }
    
    /**
     * Initializes tracing for a new request from an HTTP servlet request.
     * Extracts the correlation ID from the request headers if present,
     * otherwise generates a new one.
     *
     * @param request The HTTP servlet request
     * @return The correlation ID that was set
     */
    public static String initializeTracing(HttpServletRequest request) {
        String correlationId = extractCorrelationIdFromRequest(request);
        return initializeTracing(correlationId);
    }

    /**
     * Finalizes tracing for the current request.
     * This method should be called at the end of request processing to clean up the MDC context.
     */
    public static void finalizeTracing() {
        logger.debug("Finalizing tracing with correlation ID: {}", getCurrentCorrelationId());
        clearCurrentCorrelationId();
    }
}