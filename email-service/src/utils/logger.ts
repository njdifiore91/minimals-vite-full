/**
 * Logger Utilities for Email Service
 * 
 * This module provides utility functions for structured logging in the Email Service.
 * It builds on top of the base logger configuration to provide easy-to-use functions
 * for creating contextual log entries, formatting log messages, and handling different
 * log levels consistently across the service.
 * 
 * Key features:
 * - Simplified logging functions for different log levels
 * - Context enrichment for structured logging
 * - Request ID tracking for distributed tracing
 * - Error logging with stack traces
 * - Performance measurement utilities
 */

import { v4 as uuidv4 } from 'uuid';
import {
  logger as baseLogger,
  createChildLogger,
  createRequestLogger,
  createComponentLogger,
  logError as baseLogError,
} from '../config/logger';

/**
 * Log levels as defined in the logger configuration
 */
export enum LogLevel {
  ERROR = 'ERROR',
  WARN = 'WARN',
  INFO = 'INFO',
  DEBUG = 'DEBUG',
}

/**
 * Context interface for structured logging
 */
export interface LogContext {
  [key: string]: any;
}

/**
 * Default logger instance
 * 
 * This is the main logger instance that should be used for general logging.
 * For context-specific logging, use the createLogger function.
 */
export const logger = baseLogger;

/**
 * Create a logger with component context
 * 
 * This function creates a logger with a specific component name as context,
 * which is useful for identifying the source of log entries.
 * 
 * Example usage:
 * ```
 * const logger = createLogger('EmailProcessor');
 * logger.info('Processing email', { emailId: '123' });
 * ```
 * 
 * @param component The component name to include in logs
 * @returns A logger instance with component context
 */
export const createLogger = (component: string) => {
  return createComponentLogger(component);
};

/**
 * Create a logger with request context
 * 
 * This function creates a logger with a specific request ID as context,
 * which is essential for tracing related log entries across the email processing flow.
 * 
 * Example usage:
 * ```
 * const requestId = getRequestId();
 * const logger = createRequestLogger(requestId);
 * logger.info('Processing attachment');
 * ```
 * 
 * @param requestId The request ID to include in logs
 * @returns A logger instance with request ID context
 */
export const createRequestContextLogger = (requestId: string) => {
  return createRequestLogger(requestId);
};

/**
 * Generate a new request ID
 * 
 * This function generates a unique request ID using UUID v4,
 * which is useful for tracking a specific email processing flow.
 * 
 * Example usage:
 * ```
 * const requestId = generateRequestId();
 * const logger = createRequestContextLogger(requestId);
 * ```
 * 
 * @returns A unique request ID
 */
export const generateRequestId = (): string => {
  return uuidv4();
};

/**
 * Extract request ID from email or generate a new one
 * 
 * This function attempts to extract a request ID from email headers
 * or generates a new one if not found. This is useful for maintaining
 * request context across service boundaries.
 * 
 * @param email The email object to extract request ID from
 * @param headerName The header name to look for (default: 'X-Request-ID')
 * @returns The extracted or generated request ID
 */
export const getRequestId = (email?: any, headerName: string = 'X-Request-ID'): string => {
  if (email?.headers?.[headerName]) {
    return email.headers[headerName];
  }
  return generateRequestId();
};

/**
 * Log an error with stack trace and context
 * 
 * This function logs an error with its stack trace and additional context,
 * which is essential for debugging and troubleshooting.
 * 
 * Example usage:
 * ```
 * try {
 *   // Some code that might throw
 * } catch (error) {
 *   logError(logger, 'Failed to process email', error, { emailId: '123' });
 * }
 * ```
 * 
 * @param logger The logger instance to use
 * @param message The error message
 * @param error The error object
 * @param context Additional context to include in the log
 */
export const logError = (
  logger: any,
  message: string,
  error: Error,
  context: LogContext = {}
): void => {
  baseLogError(logger, message, error, context);
};

/**
 * Log a warning message with context
 * 
 * This function logs a warning message with additional context,
 * which is useful for potential issues that might lead to errors.
 * 
 * Example usage:
 * ```
 * logWarning(logger, 'Email size exceeds recommended limit', { size: emailSize, limit: MAX_SIZE });
 * ```
 * 
 * @param logger The logger instance to use
 * @param message The warning message
 * @param context Additional context to include in the log
 */
export const logWarning = (
  logger: any,
  message: string,
  context: LogContext = {}
): void => {
  logger.warn(message, context);
};

/**
 * Log an info message with context
 * 
 * This function logs an info message with additional context,
 * which is useful for normal operations and significant events.
 * 
 * Example usage:
 * ```
 * logInfo(logger, 'Email received', { from: email.from, subject: email.subject });
 * ```
 * 
 * @param logger The logger instance to use
 * @param message The info message
 * @param context Additional context to include in the log
 */
export const logInfo = (
  logger: any,
  message: string,
  context: LogContext = {}
): void => {
  logger.info(message, context);
};

/**
 * Log a debug message with context
 * 
 * This function logs a debug message with additional context,
 * which is useful for detailed information for troubleshooting.
 * 
 * Example usage:
 * ```
 * logDebug(logger, 'Processing attachment', { filename: attachment.filename, size: attachment.size });
 * ```
 * 
 * @param logger The logger instance to use
 * @param message The debug message
 * @param context Additional context to include in the log
 */
export const logDebug = (
  logger: any,
  message: string,
  context: LogContext = {}
): void => {
  logger.debug(message, context);
};

/**
 * Performance measurement utility
 * 
 * This class provides utilities for measuring and logging the performance of operations,
 * which is useful for identifying bottlenecks and optimizing performance.
 * 
 * Example usage:
 * ```
 * const perf = new PerformanceLogger(logger, 'EmailProcessing');
 * perf.start('processAttachments');
 * // Process attachments
 * perf.end('processAttachments');
 * ```
 */
export class PerformanceLogger {
  private timers: Record<string, number> = {};
  private logger: any;
  private component: string;

  /**
   * Create a new PerformanceLogger
   * 
   * @param logger The logger instance to use
   * @param component The component name for context
   */
  constructor(logger: any, component: string) {
    this.logger = logger;
    this.component = component;
  }

  /**
   * Start a timer for a specific operation
   * 
   * @param operation The operation name
   */
  start(operation: string): void {
    this.timers[operation] = Date.now();
    logDebug(this.logger, `Starting operation: ${operation}`, {
      component: this.component,
      operation,
      action: 'start',
    });
  }

  /**
   * End a timer and log the duration
   * 
   * @param operation The operation name
   * @param context Additional context to include in the log
   * @returns The duration in milliseconds
   */
  end(operation: string, context: LogContext = {}): number {
    const startTime = this.timers[operation];
    if (!startTime) {
      logWarning(this.logger, `Timer not started for operation: ${operation}`, {
        component: this.component,
        operation,
      });
      return 0;
    }

    const duration = Date.now() - startTime;
    delete this.timers[operation];

    logInfo(this.logger, `Completed operation: ${operation}`, {
      component: this.component,
      operation,
      durationMs: duration,
      ...context,
    });

    return duration;
  }

  /**
   * Measure the execution time of an async function
   * 
   * @param operation The operation name
   * @param fn The async function to measure
   * @param context Additional context to include in the log
   * @returns The result of the async function
   */
  async measure<T>(
    operation: string,
    fn: () => Promise<T>,
    context: LogContext = {}
  ): Promise<T> {
    this.start(operation);
    try {
      const result = await fn();
      this.end(operation, context);
      return result;
    } catch (error) {
      this.end(operation, { ...context, error: true });
      throw error;
    }
  }

  /**
   * Measure the execution time of a synchronous function
   * 
   * @param operation The operation name
   * @param fn The synchronous function to measure
   * @param context Additional context to include in the log
   * @returns The result of the synchronous function
   */
  measureSync<T>(
    operation: string,
    fn: () => T,
    context: LogContext = {}
  ): T {
    this.start(operation);
    try {
      const result = fn();
      this.end(operation, context);
      return result;
    } catch (error) {
      this.end(operation, { ...context, error: true });
      throw error;
    }
  }
}

/**
 * Create a performance logger
 * 
 * This function creates a new PerformanceLogger instance,
 * which is useful for measuring and logging the performance of operations.
 * 
 * Example usage:
 * ```
 * const perf = createPerformanceLogger(logger, 'EmailProcessing');
 * perf.measure('processEmail', async () => {
 *   // Process email
 * });
 * ```
 * 
 * @param logger The logger instance to use
 * @param component The component name for context
 * @returns A new PerformanceLogger instance
 */
export const createPerformanceLogger = (
  logger: any,
  component: string
): PerformanceLogger => {
  return new PerformanceLogger(logger, component);
};

/**
 * Log an API request with context
 * 
 * This function logs an API request with additional context,
 * which is useful for tracking external API calls.
 * 
 * Example usage:
 * ```
 * logApiRequest(logger, 'GET', 'https://api.example.com/data', { params: { id: '123' } });
 * ```
 * 
 * @param logger The logger instance to use
 * @param method The HTTP method
 * @param url The API URL
 * @param context Additional context to include in the log
 */
export const logApiRequest = (
  logger: any,
  method: string,
  url: string,
  context: LogContext = {}
): void => {
  logInfo(logger, `API Request: ${method} ${url}`, {
    api: {
      method,
      url,
      ...context,
    },
  });
};

/**
 * Log an API response with context
 * 
 * This function logs an API response with additional context,
 * which is useful for tracking external API responses.
 * 
 * Example usage:
 * ```
 * logApiResponse(logger, 'GET', 'https://api.example.com/data', 200, { responseTime: 150 });
 * ```
 * 
 * @param logger The logger instance to use
 * @param method The HTTP method
 * @param url The API URL
 * @param statusCode The HTTP status code
 * @param context Additional context to include in the log
 */
export const logApiResponse = (
  logger: any,
  method: string,
  url: string,
  statusCode: number,
  context: LogContext = {}
): void => {
  const level = statusCode >= 400 ? LogLevel.ERROR : LogLevel.INFO;
  const message = `API Response: ${method} ${url} ${statusCode}`;
  
  if (level === LogLevel.ERROR) {
    logger.error(message, {
      api: {
        method,
        url,
        statusCode,
        ...context,
      },
    });
  } else {
    logInfo(logger, message, {
      api: {
        method,
        url,
        statusCode,
        ...context,
      },
    });
  }
};

/**
 * Log a message queue event with context
 * 
 * This function logs a message queue event with additional context,
 * which is useful for tracking message publishing and consumption.
 * 
 * Example usage:
 * ```
 * logMessageQueueEvent(logger, 'publish', 'mca.documents', { messageId: '123', size: 1024 });
 * ```
 * 
 * @param logger The logger instance to use
 * @param action The message queue action (publish, consume, etc.)
 * @param exchange The message exchange
 * @param context Additional context to include in the log
 */
export const logMessageQueueEvent = (
  logger: any,
  action: string,
  exchange: string,
  context: LogContext = {}
): void => {
  logInfo(logger, `Message Queue: ${action} to ${exchange}`, {
    messageQueue: {
      action,
      exchange,
      ...context,
    },
  });
};

/**
 * Log an email processing event with context
 * 
 * This function logs an email processing event with additional context,
 * which is useful for tracking email processing flow.
 * 
 * Example usage:
 * ```
 * logEmailEvent(logger, 'received', { emailId: '123', from: 'sender@example.com' });
 * ```
 * 
 * @param logger The logger instance to use
 * @param event The email event (received, processed, etc.)
 * @param context Additional context to include in the log
 */
export const logEmailEvent = (
  logger: any,
  event: string,
  context: LogContext = {}
): void => {
  logInfo(logger, `Email ${event}`, {
    email: {
      event,
      ...context,
    },
  });
};

/**
 * Log an attachment processing event with context
 * 
 * This function logs an attachment processing event with additional context,
 * which is useful for tracking attachment processing flow.
 * 
 * Example usage:
 * ```
 * logAttachmentEvent(logger, 'extracted', { attachmentId: '123', filename: 'document.pdf', size: 1024 });
 * ```
 * 
 * @param logger The logger instance to use
 * @param event The attachment event (extracted, uploaded, etc.)
 * @param context Additional context to include in the log
 */
export const logAttachmentEvent = (
  logger: any,
  event: string,
  context: LogContext = {}
): void => {
  logInfo(logger, `Attachment ${event}`, {
    attachment: {
      event,
      ...context,
    },
  });
};

/**
 * Create a logger with correlation context
 * 
 * This function creates a logger with correlation IDs as context,
 * which is useful for tracing related log entries across service boundaries.
 * 
 * Example usage:
 * ```
 * const logger = createCorrelationLogger({
 *   requestId: '123',
 *   emailId: '456',
 *   traceId: '789',
 * });
 * ```
 * 
 * @param correlationIds The correlation IDs to include in logs
 * @returns A logger instance with correlation context
 */
export const createCorrelationLogger = (correlationIds: Record<string, string>) => {
  return createChildLogger(correlationIds);
};

/**
 * Default export for convenience
 */
export default logger;