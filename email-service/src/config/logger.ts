/**
 * Logger Configuration for Email Service
 * 
 * This module configures the logging system for the Email Service using Winston.
 * It defines log levels, formats, transports, and context enrichment to enable
 * comprehensive logging for monitoring, debugging, and troubleshooting.
 */

import winston from 'winston';
import 'winston-daily-rotate-file';
import path from 'path';
import { existsSync, mkdirSync } from 'fs';

// Define log directory
const LOG_DIR = process.env.LOG_DIR || 'logs';

// Create log directory if it doesn't exist
if (!existsSync(LOG_DIR)) {
  mkdirSync(LOG_DIR, { recursive: true });
}

// Define log levels according to RFC5424
const levels = {
  error: 0,  // Error conditions
  warn: 1,   // Warning conditions
  info: 2,   // Informational messages
  debug: 3   // Debug-level messages
};

// Define level colors for console output
const colors = {
  error: 'red',
  warn: 'yellow',
  info: 'green',
  debug: 'blue'
};

// Add colors to winston
winston.addColors(colors);

/**
 * Custom format that combines multiple winston formats
 * - timestamp: Adds ISO timestamp
 * - errors: Preserves error stack traces
 * - json: Formats logs as JSON for machine readability
 * - colorize: Adds colors to console output (only for console transport)
 */
const logFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }),
  winston.format.errors({ stack: true }),
  winston.format.printf((info) => {
    // Add service name and format message
    const { timestamp, level, message, ...rest } = info;
    const serviceName = 'email-service';
    
    // Format the log message
    return JSON.stringify({
      timestamp,
      service: serviceName,
      level,
      message,
      ...(Object.keys(rest).length > 0 ? { context: rest } : {})
    });
  })
);

// Console format with colors for better readability in development
const consoleFormat = winston.format.combine(
  winston.format.colorize({ all: true }),
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }),
  winston.format.printf((info) => {
    const { timestamp, level, message, ...rest } = info;
    const serviceName = 'email-service';
    const contextStr = Object.keys(rest).length > 0 
      ? `\n${JSON.stringify(rest, null, 2)}` 
      : '';
    
    return `[${timestamp}] [${serviceName}] ${level}: ${message}${contextStr}`;
  })
);

// Define transports based on environment
const transports: winston.transport[] = [
  // Console transport (always enabled)
  new winston.transports.Console({
    format: consoleFormat
  })
];

// Add file transports in production and staging environments
if (process.env.NODE_ENV === 'production' || process.env.NODE_ENV === 'staging') {
  // Daily rotate file transport for all logs
  transports.push(
    new winston.transports.DailyRotateFile({
      filename: path.join(LOG_DIR, 'email-service-%DATE%.log'),
      datePattern: 'YYYY-MM-DD',
      maxSize: '20m',
      maxFiles: '14d',
      format: logFormat
    })
  );
  
  // Daily rotate file transport for error logs only
  transports.push(
    new winston.transports.DailyRotateFile({
      filename: path.join(LOG_DIR, 'email-service-error-%DATE%.log'),
      datePattern: 'YYYY-MM-DD',
      maxSize: '20m',
      maxFiles: '30d',
      level: 'error',
      format: logFormat
    })
  );
}

// Create the logger instance
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  levels,
  format: logFormat,
  transports,
  // Don't exit on handled exceptions
  exitOnError: false
});

/**
 * Creates a child logger with additional context
 * @param context Additional context to include in all log messages
 * @returns A child logger with the provided context
 */
export function createChildLogger(context: Record<string, any>) {
  return logger.child(context);
}

/**
 * Adds request tracking to the logger
 * @param requestId Unique identifier for the request
 * @returns A child logger with request tracking
 */
export function createRequestLogger(requestId: string) {
  return createChildLogger({ requestId });
}

/**
 * Logs an uncaught exception with full stack trace
 * @param err The uncaught exception
 * @param origin The origin of the exception
 */
export function logUncaughtException(err: Error, origin: string) {
  logger.error('Uncaught exception', {
    error: err.message,
    stack: err.stack,
    origin
  });
}

/**
 * Logs an unhandled promise rejection
 * @param reason The rejection reason
 * @param promise The rejected promise
 */
export function logUnhandledRejection(reason: any, promise: Promise<any>) {
  logger.error('Unhandled promise rejection', {
    reason: reason instanceof Error ? reason.message : reason,
    stack: reason instanceof Error ? reason.stack : undefined,
    promise
  });
}

export default logger;