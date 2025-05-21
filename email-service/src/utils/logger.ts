/**
 * Logger utility functions for the Email Service
 * 
 * This module provides utility functions for structured logging with context information,
 * error logging with stack traces, and request ID tracking for distributed tracing.
 * It works with the logger configuration defined in src/config/logger.ts.
 *
 * The utility functions in this module help maintain consistent logging practices across
 * the Email Service, ensuring that all logs include necessary context information and
 * follow the specified log level guidelines (ERROR, WARN, INFO, DEBUG).
 */

import { fDateTime } from './format-time';

// Types for logger context and log levels
export type LogContext = Record<string, any>;

export enum LogLevel {
  ERROR = 'error',
  WARN = 'warn',
  INFO = 'info',
  DEBUG = 'debug'
}

/**
 * Creates a context object for logging with standard fields
 * @param context Additional context information to include in logs
 * @returns A context object with standard fields
 */
export function createLogContext(context: LogContext = {}): LogContext {
  return {
    timestamp: fDateTime(new Date(), 'YYYY-MM-DD HH:mm:ss.SSS'),
    service: 'email-service',
    environment: process.env.NODE_ENV || 'development',
    pid: process.pid,
    hostname: process.env.HOSTNAME || 'localhost',
    ...context
  };
}

/**
 * Creates a log entry with request ID for distributed tracing
 * @param requestId The request ID for distributed tracing
 * @param context Additional context information
 * @returns A log context with request ID
 */
export function createRequestContext(requestId: string, context: LogContext = {}): LogContext {
  return createLogContext({
    requestId,
    ...context
  });
}

/**
 * Formats an error object for logging, including stack trace
 * @param error The error object to format
 * @param context Additional context information
 * @returns A log context with error details
 */
export function formatError(error: Error, context: LogContext = {}): LogContext {
  // Extract additional properties from error object if they exist
  const errorDetails: Record<string, any> = {
    name: error.name,
    message: error.message,
    stack: error.stack
  };

  // Add any additional properties from the error object
  for (const key in error) {
    if (Object.prototype.hasOwnProperty.call(error, key) && !errorDetails[key]) {
      // @ts-ignore - We're intentionally extracting custom properties
      errorDetails[key] = error[key];
    }
  }

  return {
    ...createLogContext(context),
    error: errorDetails
  };
}

/**
 * Formats a log message with context information
 * @param message The log message
 * @param context Additional context information
 * @returns A formatted log object
 */
export function formatLogMessage(message: string, context: LogContext = {}): { message: string; context: LogContext } {
  return {
    message,
    context: createLogContext(context)
  };
}

/**
 * Formats a log message as a JSON string
 * @param message The log message
 * @param level The log level
 * @param context Additional context information
 * @returns A JSON string representation of the log entry
 */
export function formatLogAsJson(message: string, level: LogLevel, context: LogContext = {}): string {
  const logEntry = {
    level,
    message,
    ...createLogContext(context)
  };
  
  return JSON.stringify(logEntry);
}

/**
 * Formats a log message for machine parsing with consistent field ordering
 * @param message The log message
 * @param level The log level
 * @param context Additional context information
 * @returns A formatted string for machine parsing
 */
export function formatLogForMachine(message: string, level: LogLevel, context: LogContext = {}): string {
  const timestamp = fDateTime(new Date(), 'YYYY-MM-DD HH:mm:ss.SSS');
  const logContext = sanitizeLogContext(context);
  const contextStr = Object.entries(logContext)
    .map(([key, value]) => `${key}=${typeof value === 'object' ? JSON.stringify(value) : value}`)
    .join(' ');
  
  return `${timestamp} [${level.toUpperCase()}] [email-service] ${message} ${contextStr}`;
}

/**
 * Creates a child logger with predefined context
 * @param baseContext The base context to include in all logs from this logger
 * @returns An object with logging functions that include the base context
 */
export function createContextLogger(baseContext: LogContext = {}) {
  // Sanitize the base context to ensure no sensitive data is included
  const sanitizedBaseContext = sanitizeLogContext(baseContext);
  
  return {
    /**
     * Log an error message with optional error object and context
     * @param message The error message
     * @param error Optional error object to include stack trace and details
     * @param context Additional context for this specific log
     */
    error: (message: string, error?: Error, context: LogContext = {}) => {
      const combinedContext = { ...sanitizedBaseContext, ...sanitizeLogContext(context) };
      return error ? formatError(error, combinedContext) : formatLogMessage(message, combinedContext);
    },
    
    /**
     * Log a warning message with optional context
     * @param message The warning message
     * @param context Additional context for this specific log
     */
    warn: (message: string, context: LogContext = {}) => {
      return formatLogMessage(message, { ...sanitizedBaseContext, ...sanitizeLogContext(context) });
    },
    
    /**
     * Log an informational message with optional context
     * @param message The info message
     * @param context Additional context for this specific log
     */
    info: (message: string, context: LogContext = {}) => {
      return formatLogMessage(message, { ...sanitizedBaseContext, ...sanitizeLogContext(context) });
    },
    
    /**
     * Log a debug message with optional context
     * @param message The debug message
     * @param context Additional context for this specific log
     */
    debug: (message: string, context: LogContext = {}) => {
      return formatLogMessage(message, { ...sanitizedBaseContext, ...sanitizeLogContext(context) });
    },
    
    /**
     * Create a new logger with additional context merged with the current context
     * @param additionalContext Additional context to merge with the current context
     */
    withContext: (additionalContext: LogContext) => {
      return createContextLogger({ ...sanitizedBaseContext, ...sanitizeLogContext(additionalContext) });
    }
  };
}

/**
 * Log level priorities - lower numbers are higher priority
 */
export const LOG_LEVEL_PRIORITIES = {
  [LogLevel.ERROR]: 0,
  [LogLevel.WARN]: 1,
  [LogLevel.INFO]: 2,
  [LogLevel.DEBUG]: 3
};

/**
 * Determines if a log level should be logged based on the current environment configuration
 * @param level The log level to check
 * @param configuredLevel The configured minimum log level
 * @returns True if the log level should be logged
 */
export function shouldLog(level: LogLevel, configuredLevel: LogLevel): boolean {
  return LOG_LEVEL_PRIORITIES[level] <= LOG_LEVEL_PRIORITIES[configuredLevel];
}

/**
 * Gets the appropriate log level based on the environment
 * @returns The log level appropriate for the current environment
 */
export function getLogLevelForEnvironment(): LogLevel {
  const env = process.env.NODE_ENV || 'development';
  
  switch (env) {
    case 'production':
      return LogLevel.INFO; // In production, log INFO and above
    case 'staging':
      return LogLevel.INFO; // In staging, log INFO and above
    case 'test':
      return LogLevel.WARN; // In test, log WARN and above to reduce noise
    case 'development':
    default:
      return LogLevel.DEBUG; // In development, log everything
  }
}

/**
 * Default sensitive keys that should be redacted from logs
 * This list includes common patterns for sensitive information
 */
export const DEFAULT_SENSITIVE_KEYS = [
  'password',
  'token',
  'secret',
  'key',
  'credential',
  'auth',
  'private',
  'cert',
  'ssn',
  'social',
  'ein',
  'tax',
  'account',
  'card',
  'cvv',
  'passport'
];

/**
 * Sanitizes sensitive data from log context
 * @param context The log context to sanitize
 * @param sensitiveKeys Array of sensitive key patterns to redact
 * @returns Sanitized log context
 */
export function sanitizeLogContext(
  context: LogContext, 
  sensitiveKeys: string[] = DEFAULT_SENSITIVE_KEYS
): LogContext {
  // If context is null or undefined, return an empty object
  if (!context) return {};
  
  const sanitized = { ...context };
  
  const redactNestedObject = (obj: Record<string, any>, path: string = '') => {
    for (const [key, value] of Object.entries(obj)) {
      const currentPath = path ? `${path}.${key}` : key;
      
      // Check if the current key matches any sensitive key pattern
      const isSensitive = sensitiveKeys.some(pattern => 
        key.toLowerCase().includes(pattern.toLowerCase())
      );
      
      if (isSensitive) {
        obj[key] = '[REDACTED]';
      } else if (value && typeof value === 'object' && !Array.isArray(value)) {
        // Recursively check nested objects
        redactNestedObject(value, currentPath);
      } else if (Array.isArray(value)) {
        // Check each item in the array if it's an object
        for (let i = 0; i < value.length; i++) {
          if (value[i] && typeof value[i] === 'object') {
            redactNestedObject(value[i], `${currentPath}[${i}]`);
          }
        }
      }
    }
  };
  
  redactNestedObject(sanitized);
  return sanitized;
}

/**
 * Creates a logger for a specific module or component
 * @param moduleName The name of the module or component
 * @returns A logger with the module name in context
 */
export function createModuleLogger(moduleName: string) {
  return createContextLogger({ module: moduleName });
}

/**
 * Creates a logger for tracking email processing
 * @param emailId The ID of the email being processed
 * @param additionalContext Additional context information
 * @returns A logger with email tracking context
 */
export function createEmailLogger(emailId: string, additionalContext: LogContext = {}) {
  return createContextLogger({
    emailId,
    operation: 'email-processing',
    ...additionalContext
  });
}

/**
 * Creates a logger for tracking attachment processing
 * @param emailId The ID of the email containing the attachment
 * @param attachmentId The ID of the attachment being processed
 * @param additionalContext Additional context information
 * @returns A logger with attachment tracking context
 */
export function createAttachmentLogger(emailId: string, attachmentId: string, additionalContext: LogContext = {}) {
  return createContextLogger({
    emailId,
    attachmentId,
    operation: 'attachment-processing',
    ...additionalContext
  });
}

/**
 * Creates a logger for tracking message queue operations
 * @param operation The message queue operation (publish, subscribe, etc.)
 * @param exchange The message exchange being used
 * @param additionalContext Additional context information
 * @returns A logger with message queue context
 */
export function createMessageQueueLogger(operation: string, exchange: string, additionalContext: LogContext = {}) {
  return createContextLogger({
    operation: `mq-${operation}`,
    exchange,
    ...additionalContext
  });
}