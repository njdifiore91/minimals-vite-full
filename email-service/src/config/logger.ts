/**
 * Logger Configuration for Email Service
 * 
 * This module configures the logging system for the Email Service microservice.
 * It sets up appropriate log levels, formats, and transports based on the environment.
 * The logger includes timestamps, service name, and context information for comprehensive
 * monitoring, debugging, and troubleshooting.
 * 
 * Log levels:
 * - ERROR: Processing failures and critical issues that require immediate attention
 * - WARN: Potential issues that might lead to errors if not addressed
 * - INFO: Normal operations and significant events (default in production)
 * - DEBUG: Detailed information for troubleshooting (only in development)
 */

import winston from 'winston';
import { format } from 'winston';
import path from 'path';

/**
 * Define log levels matching the requirements in section 0.2.5
 * Lower values indicate higher severity
 */
const logLevels = {
  ERROR: 0, // Processing failures
  WARN: 1,  // Potential issues
  INFO: 2,  // Normal operations
  DEBUG: 3, // Troubleshooting (development only)
};

/**
 * Define log level colors for console output to improve readability
 */
const logColors = {
  ERROR: 'red',
  WARN: 'yellow',
  INFO: 'green',
  DEBUG: 'blue',
};

// Add colors to Winston
winston.addColors(logColors);

/**
 * Custom format for formatting error objects
 * 
 * This formatter ensures that Error objects are properly serialized with their
 * stack traces, which is essential for debugging and troubleshooting.
 * It handles both direct Error objects and errors nested in the 'error' property.
 */
const errorFormat = format((info) => {
  if (info instanceof Error) {
    return {
      ...info,
      message: info.message,
      stack: info.stack,
    };
  }
  if (info.error instanceof Error) {
    return {
      ...info,
      error: {
        message: info.error.message,
        stack: info.error.stack,
        ...info.error,
      },
    };
  }
  return info;
})();

/**
 * Custom format for adding request ID to logs
 * 
 * This formatter adds a request ID to log entries when provided, which is crucial
 * for tracing related log entries across a distributed system. This enables
 * correlation of logs for a specific email processing flow.
 */
const requestIdFormat = format((info, opts) => {
  if (opts.requestId) {
    info.requestId = opts.requestId;
  }
  return info;
});

/**
 * Get the appropriate log level based on environment
 * 
 * This function determines the log level based on the LOG_LEVEL environment variable
 * or falls back to environment-specific defaults if not specified.
 * 
 * As per section 0.2.5 of the technical specification:
 * - Production: INFO level for normal operations
 * - Staging: INFO level for normal operations
 * - Test: WARN level to reduce noise during tests
 * - Development: DEBUG level for detailed troubleshooting
 * 
 * @returns The appropriate log level as a string
 */
const getLogLevel = (): string => {
  const level = process.env.LOG_LEVEL?.toUpperCase();
  if (level && Object.keys(logLevels).includes(level)) {
    return level;
  }
  
  // Default log levels based on environment
  switch (process.env.NODE_ENV) {
    case 'production':
      return 'INFO';
    case 'staging':
      return 'INFO';
    case 'test':
      return 'WARN';
    case 'development':
    default:
      return 'DEBUG';
  }
};

/**
 * Configure transports based on environment
 * 
 * This function sets up the appropriate logging transports based on the environment:
 * - Console transport: Used in all environments with colorized output for better readability
 * - File transports: Used in production and staging environments for persistent logging
 *   - combined.log: Contains all log levels
 *   - error.log: Contains only ERROR level logs for quick access to critical issues
 * 
 * In production, logs are formatted as JSON for easier parsing by log aggregation tools.
 * 
 * @returns An array of configured Winston transports
 */
const getTransports = () => {
  const transports: winston.transport[] = [];
  
  // Console transport - used in all environments
  transports.push(
    new winston.transports.Console({
      format: format.combine(
        format.colorize({ all: true }),
        format.timestamp(),
        format.printf(({ timestamp, level, message, requestId, ...meta }) => {
          const reqId = requestId ? `[${requestId}]` : '';
          const metaStr = Object.keys(meta).length ? `\n${JSON.stringify(meta, null, 2)}` : '';
          return `${timestamp} ${level} [Email Service]${reqId}: ${message}${metaStr}`;
        })
      ),
    })
  );
  
  // File transport - only used in production and staging
  if (['production', 'staging'].includes(process.env.NODE_ENV || '')) {
    // Log all levels to combined log
    transports.push(
      new winston.transports.File({
        filename: path.join(process.env.LOG_DIR || 'logs', 'combined.log'),
        format: format.combine(
          format.timestamp(),
          format.json()
        ),
        maxsize: 10485760, // 10MB
        maxFiles: 10,
        tailable: true,
      })
    );
    
    // Log only errors to error log
    transports.push(
      new winston.transports.File({
        filename: path.join(process.env.LOG_DIR || 'logs', 'error.log'),
        level: 'ERROR',
        format: format.combine(
          format.timestamp(),
          format.json()
        ),
        maxsize: 10485760, // 10MB
        maxFiles: 10,
        tailable: true,
      })
    );
  }
  
  return transports;
};

/**
 * Create the base logger instance
 * 
 * This function creates a configured Winston logger instance with the appropriate
 * levels, formats, and transports. It also adds default metadata to all log entries,
 * including the service name and environment.
 * 
 * @param options Options for the logger, including requestId for request tracking
 * @returns A configured Winston logger instance
 */
export const createLogger = (options: { requestId?: string } = {}) => {
  return winston.createLogger({
    levels: logLevels,
    level: getLogLevel(),
    format: format.combine(
      errorFormat,
      requestIdFormat(options),
      format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }),
      format.json()
    ),
    defaultMeta: {
      service: 'email-service',
      environment: process.env.NODE_ENV || 'development',
      version: process.env.npm_package_version || '1.0.0',
      hostname: process.env.HOSTNAME || 'unknown',
    },
    transports: getTransports(),
    exitOnError: false, // Don't exit on handled exceptions
  });
};

/**
 * Default logger instance
 * 
 * This is the main logger instance that should be imported and used throughout the application.
 * For context-specific logging, use createChildLogger or createRequestLogger.
 */
export const logger = createLogger();

/**
 * Create a child logger with additional context
 * 
 * This function creates a child logger with additional context information,
 * which is useful for adding component-specific or flow-specific metadata to logs.
 * 
 * Example usage:
 * ```
 * const emailLogger = createChildLogger({ component: 'email-processor' });
 * emailLogger.info('Processing email', { emailId: '123' });
 * ```
 * 
 * @param context Additional context to add to log entries
 * @returns A child logger instance with the provided context
 */
export const createChildLogger = (context: Record<string, any>) => {
  return logger.child(context);
};

/**
 * Create a request-scoped logger with request ID
 * 
 * This function creates a logger instance with a specific request ID,
 * which is essential for tracing related log entries across the email processing flow.
 * 
 * Example usage:
 * ```
 * const requestId = uuidv4();
 * const reqLogger = createRequestLogger(requestId);
 * reqLogger.info('Processing attachment');
 * ```
 * 
 * @param requestId The request ID to include in logs
 * @returns A logger instance with request ID context
 */
export const createRequestLogger = (requestId: string) => {
  return createLogger({ requestId });
};

/**
 * Create a component logger with component name as context
 * 
 * This is a convenience function for creating a logger for a specific component,
 * which is a common pattern in microservices.
 * 
 * Example usage:
 * ```
 * const logger = createComponentLogger('EmailProcessor');
 * logger.info('Starting email processing');
 * ```
 * 
 * @param componentName The name of the component
 * @returns A logger instance with the component name as context
 */
export const createComponentLogger = (componentName: string) => {
  return createChildLogger({ component: componentName });
};

/**
 * Log an error with additional context
 * 
 * This is a utility function for logging errors with consistent formatting.
 * It ensures that the error stack trace is properly captured and logged.
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
  logger: winston.Logger,
  message: string,
  error: Error,
  context: Record<string, any> = {}
) => {
  logger.error(message, {
    error: {
      name: error.name,
      message: error.message,
      stack: error.stack,
    },
    ...context,
  });
};

/**
 * Export a singleton logger instance as the default export
 */
export default logger;