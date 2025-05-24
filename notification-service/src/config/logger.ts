/**
 * Logger Configuration for Notification Service
 *
 * This file configures the logging system for the Notification Service. It defines log levels,
 * formats, transports, and context enrichment. It enables comprehensive logging for monitoring,
 * debugging, and troubleshooting the service's operation, ensuring that all processing failures,
 * potential issues, and normal operations are properly recorded.
 */

import winston from 'winston';
import 'winston-daily-rotate-file';
import path from 'path';
import fs from 'fs';
import { config } from './app';
import { LogLevel } from '../types/config';

/**
 * Ensure log directory exists
 */
const logDir = path.dirname(config.logger.filePath || 'logs');
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

/**
 * Define log formats
 */
const formats = {
  // Format for development environment (colorized, pretty-printed)
  development: winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }),
    winston.format.colorize(),
    winston.format.printf(({ timestamp, level, message, ...meta }) => {
      const metaString = Object.keys(meta).length ? `\n${JSON.stringify(meta, null, 2)}` : '';
      return `${timestamp} [${level}]: ${message}${metaString}`;
    })
  ),

  // Format for production environment (JSON format for machine parsing)
  production: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
};

/**
 * Configure transports based on environment
 */
const transports: winston.transport[] = [];

// Console transport (always enabled in development, optional in production)
if (config.logger.console) {
  transports.push(
    new winston.transports.Console({
      level: config.logger.level,
      format: config.app.environment === 'development' ? formats.development : formats.production,
    })
  );
}

// File transport (if configured)
if (config.logger.filePath) {
  // Regular file transport
  transports.push(
    new winston.transports.File({
      filename: config.logger.filePath,
      level: config.logger.level,
      format: formats.production,
      maxsize: config.logger.maxFileSize,
      maxFiles: config.logger.maxFiles,
    })
  );

  // Daily rotate file transport for production
  if (config.app.environment === 'production' || config.app.environment === 'staging') {
    const rotateFilePath = config.logger.filePath.replace(/\.log$/, '-%DATE%.log');
    transports.push(
      new winston.transports.DailyRotateFile({
        filename: rotateFilePath,
        datePattern: 'YYYY-MM-DD',
        zippedArchive: true,
        maxSize: `${Math.floor(config.logger.maxFileSize / 1024 / 1024)}m`,
        maxFiles: `${config.logger.maxFiles}d`,
        level: config.logger.level,
        format: formats.production,
      })
    );
  }
}

/**
 * Create the logger instance
 */
export const logger = winston.createLogger({
  level: config.logger.level,
  defaultMeta: {
    service: config.app.name,
    version: config.app.version,
    environment: config.app.environment,
    ...config.logger.defaultMeta,
  },
  transports,
  // Exit on error should be false for production to prevent crashing
  exitOnError: false,
});

/**
 * Create a child logger with additional context
 * @param context Additional context to include in log entries
 * @returns A child logger with the provided context
 */
export const createChildLogger = (context: Record<string, any>) => {
  return logger.child(context);
};

/**
 * Create a request-scoped logger with correlation ID
 * @param correlationId Request correlation ID for distributed tracing
 * @param requestId Optional request ID
 * @returns A child logger with request context
 */
export const createRequestLogger = (correlationId: string, requestId?: string) => {
  return createChildLogger({
    correlationId,
    requestId: requestId || correlationId,
    timestamp: new Date().toISOString(),
  });
};

/**
 * Redact sensitive information from log entries
 * @param obj Object to redact
 * @returns Redacted object
 */
export const redactSensitiveInfo = (obj: Record<string, any>): Record<string, any> => {
  const result = { ...obj };
  const redactPatterns = config.logger.redactPatterns;

  const redact = (obj: Record<string, any>, path = ''): Record<string, any> => {
    const result = { ...obj };

    for (const key in result) {
      const currentPath = path ? `${path}.${key}` : key;
      
      // Check if the current key matches any redact pattern
      const shouldRedact = redactPatterns.some(pattern => pattern.test(key));
      
      if (shouldRedact) {
        result[key] = '[REDACTED]';
      } else if (typeof result[key] === 'object' && result[key] !== null) {
        result[key] = redact(result[key], currentPath);
      }
    }

    return result;
  };

  return redact(result);
};

/**
 * Log levels mapped to their respective methods
 */
export const logLevels = {
  [LogLevel.ERROR]: logger.error.bind(logger),
  [LogLevel.WARN]: logger.warn.bind(logger),
  [LogLevel.INFO]: logger.info.bind(logger),
  [LogLevel.DEBUG]: logger.debug.bind(logger),
};

/**
 * Helper function to log errors with stack traces
 * @param message Error message
 * @param error Error object
 * @param meta Additional metadata
 */
export const logError = (message: string, error: Error, meta: Record<string, any> = {}) => {
  logger.error(message, {
    error: {
      name: error.name,
      message: error.message,
      stack: error.stack,
    },
    ...redactSensitiveInfo(meta),
  });
};

/**
 * Helper function to log webhook delivery results
 * @param webhookId Webhook ID
 * @param success Whether delivery was successful
 * @param statusCode HTTP status code
 * @param responseTime Response time in milliseconds
 * @param meta Additional metadata
 */
export const logWebhookDelivery = (
  webhookId: string,
  success: boolean,
  statusCode: number,
  responseTime: number,
  meta: Record<string, any> = {}
) => {
  const level = success ? LogLevel.INFO : LogLevel.ERROR;
  const logMethod = logLevels[level];
  
  logMethod(`Webhook delivery ${success ? 'succeeded' : 'failed'} for webhook ${webhookId}`, {
    webhookId,
    success,
    statusCode,
    responseTime,
    ...redactSensitiveInfo(meta),
  });
};

/**
 * Helper function to log message processing events
 * @param messageId Message ID
 * @param status Processing status
 * @param meta Additional metadata
 */
export const logMessageProcessing = (
  messageId: string,
  status: 'received' | 'processing' | 'completed' | 'failed',
  meta: Record<string, any> = {}
) => {
  const level = status === 'failed' ? LogLevel.ERROR : LogLevel.INFO;
  const logMethod = logLevels[level];
  
  logMethod(`Message ${status}`, {
    messageId,
    status,
    ...redactSensitiveInfo(meta),
  });
};

// Export default logger
export default logger;