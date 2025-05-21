/**
 * @file error.ts
 * @description TypeScript interfaces for error handling, logging, and monitoring used by the Email Service.
 * Provides type definitions for standardized error structures, logging formats, and error classification.
 */

/**
 * Error severity levels for classification and monitoring
 */
export enum ErrorSeverity {
  CRITICAL = 'CRITICAL', // System-critical errors requiring immediate attention
  HIGH = 'HIGH',         // Serious errors affecting core functionality
  MEDIUM = 'MEDIUM',     // Errors affecting some functionality but not critical operations
  LOW = 'LOW',           // Minor errors with minimal impact
}

/**
 * Error categories for classification and filtering
 */
export enum ErrorCategory {
  NETWORK = 'NETWORK',           // Network-related errors (IMAP connection, etc.)
  AUTHENTICATION = 'AUTH',       // Authentication-related errors
  VALIDATION = 'VALIDATION',     // Data validation errors
  PROCESSING = 'PROCESSING',     // Email processing errors
  DATABASE = 'DATABASE',         // Database-related errors
  MESSAGING = 'MESSAGING',       // Message queue related errors
  SYSTEM = 'SYSTEM',             // System-level errors
  EXTERNAL = 'EXTERNAL',         // Errors from external services
  UNKNOWN = 'UNKNOWN',           // Unclassified errors
}

/**
 * Log levels as specified in technical specification section 0.2.5
 */
export enum LogLevel {
  ERROR = 'ERROR',   // Processing failures
  WARN = 'WARN',     // Potential issues
  INFO = 'INFO',     // Normal operations
  DEBUG = 'DEBUG',   // Troubleshooting (development only)
}

/**
 * Interface for detailed error information
 */
export interface IErrorDetails {
  message: string;                 // Human-readable error message
  code?: string;                   // Error code for programmatic handling
  stack?: string;                  // Error stack trace
  timestamp: string;               // ISO timestamp when error occurred
  context?: Record<string, any>;   // Additional context information
  originalError?: Error | unknown; // Original error object if available
}

/**
 * Interface for standardized service errors
 */
export interface IServiceError {
  id: string;                      // Unique error identifier
  message: string;                 // Human-readable error message
  code: string;                    // Error code for programmatic handling
  severity: ErrorSeverity;         // Error severity level
  category: ErrorCategory;         // Error category for classification
  details: IErrorDetails;          // Detailed error information
  retryable: boolean;              // Whether the operation can be retried
  source: string;                  // Source of the error (service/component name)
}

/**
 * Interface for structured log entries
 */
export interface ILogEntry {
  timestamp: string;               // ISO timestamp of the log entry
  level: LogLevel;                 // Log level
  message: string;                 // Log message
  service: string;                 // Service name (always 'email-service')
  context?: Record<string, any>;   // Additional context information
  correlationId?: string;          // Request correlation ID for tracing
  error?: IErrorDetails;           // Error details if applicable
}

/**
 * Interface for error monitoring metrics
 */
export interface IErrorMetrics {
  errorCount: number;              // Total error count
  errorsByCategory: Record<ErrorCategory, number>; // Errors grouped by category
  errorsBySeverity: Record<ErrorSeverity, number>; // Errors grouped by severity
  lastErrorTimestamp?: string;     // Timestamp of the last error
  serviceHealth: 'healthy' | 'degraded' | 'unhealthy'; // Overall service health status
  timeWindow: number;              // Time window in milliseconds for metrics collection
}

/**
 * Interface for alert notification configuration
 */
export interface IAlertConfig {
  enabled: boolean;                // Whether alerts are enabled
  minSeverity: ErrorSeverity;      // Minimum severity level to trigger alerts
  channels: string[];              // Alert notification channels
  throttleMs: number;              // Throttle period in milliseconds
  groupSimilarErrors: boolean;     // Whether to group similar errors
  recipients?: string[];           // Email recipients for alerts
  webhookUrls?: string[];          // Webhook URLs for alert notifications
}

/**
 * Interface for retry configuration
 */
export interface IRetryConfig {
  maxRetries: number;              // Maximum number of retry attempts
  initialDelayMs: number;          // Initial delay before first retry
  backoffFactor: number;           // Exponential backoff factor
  maxDelayMs: number;              // Maximum delay between retries
  retryableCategories: ErrorCategory[]; // Error categories eligible for retry
}

/**
 * Interface for error response sent to clients
 */
export interface IErrorResponse {
  status: 'error';                 // Status indicator
  message: string;                 // User-friendly error message
  code: string;                    // Error code
  timestamp: string;               // ISO timestamp
  requestId?: string;              // Request ID for tracking
  details?: Record<string, any>;   // Optional details (only in development)
}