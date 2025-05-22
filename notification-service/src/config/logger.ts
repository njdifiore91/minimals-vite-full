/**
 * Logger configuration for the Notification Service
 * 
 * This file configures the logging system with different levels, formats, and transports
 * based on the environment. It enables comprehensive logging for monitoring, debugging,
 * and troubleshooting the service's operation.
 */

import * as winston from 'winston';
import * as path from 'path';
import * as fs from 'fs';
import { LogLevel, ILoggerConfig } from '../types/config';
import { ILogContext } from '../types/common';

// Ensure logs directory exists
const logDir = path.join(process.cwd(), 'logs');
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

/**
 * Determine the appropriate log level based on the environment
 * - ERROR: Processing failures (always enabled)
 * - WARN: Potential issues (always enabled)
 * - INFO: Normal operations (enabled in staging and production)
 * - DEBUG: Troubleshooting (only enabled in development)
 */
const getLogLevel = (): LogLevel => {
  const env = process.env.NODE_ENV || 'development';
  
  switch (env) {
    case 'development':
      return LogLevel.DEBUG;
    case 'test':
      return LogLevel.WARN;
    case 'staging':
    case 'production':
    default:
      return LogLevel.INFO;
  }
};

/**
 * Create a custom format that includes timestamp, service name, and context information
 */
const createLogFormat = (colorize: boolean = false) => {
  const formats = [
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }),
    winston.format.errors({ stack: true }),
    winston.format((info) => {
      // Add service name to all logs
      info.service = 'notification-service';
      return info;
    })(),
    winston.format((info) => {
      // Redact sensitive information
      if (info.metadata && info.metadata.headers) {
        if (info.metadata.headers.authorization) {
          info.metadata.headers.authorization = '[REDACTED]';
        }
        if (info.metadata.headers.cookie) {
          info.metadata.headers.cookie = '[REDACTED]';
        }
      }
      return info;
    })()
  ];

  // Add colorization for console output if enabled
  if (colorize) {
    formats.push(winston.format.colorize());
  }

  // Add the final format (JSON for production, pretty print for development)
  if (process.env.NODE_ENV === 'development') {
    formats.push(
      winston.format.printf((info) => {
        const { timestamp, level, message, service, correlationId, ...rest } = info;
        const contextInfo = correlationId ? `[${correlationId}]` : '';
        const metaInfo = Object.keys(rest).length ? `\n${JSON.stringify(rest, null, 2)}` : '';
        return `${timestamp} [${service}] ${level} ${contextInfo}: ${message}${metaInfo}`;
      })
    );
  } else {
    formats.push(winston.format.json());
  }

  return winston.format.combine(...formats);
};

/**
 * Create transports based on environment
 * - Console transport for all environments (with different formatting)
 * - File transport for staging and production
 * - Datadog transport for production (if configured)
 */
const createTransports = (config: ILoggerConfig) => {
  const transports: winston.transport[] = [];

  // Console transport (always enabled)
  transports.push(
    new winston.transports.Console({
      level: config.level,
      format: createLogFormat(config.colorize),
    })
  );

  // File transport (for staging and production)
  if (config.filePath && (process.env.NODE_ENV === 'staging' || process.env.NODE_ENV === 'production')) {
    transports.push(
      new winston.transports.File({
        filename: config.filePath,
        level: config.level,
        format: createLogFormat(false),
        maxsize: config.maxFileSize || 5242880, // 5MB default
        maxFiles: config.maxFiles || 5,
      })
    );
  }

  // Datadog transport (for production if API key is provided)
  if (process.env.DATADOG_API_KEY && process.env.NODE_ENV === 'production') {
    try {
      // Dynamically import the datadog-winston package to avoid dependency issues
      // if the package is not installed
      const DatadogWinston = require('datadog-winston');
      
      transports.push(
        new DatadogWinston({
          apiKey: process.env.DATADOG_API_KEY,
          hostname: process.env.HOSTNAME || 'notification-service',
          service: 'notification-service',
          ddsource: 'nodejs',
          ddtags: `env:${process.env.NODE_ENV},service:notification-service`,
        })
      );
    } catch (error) {
      // Log to console if datadog-winston package is not available
      console.warn('Datadog transport could not be initialized:', error);
    }
  }

  return transports;
};

/**
 * Default logger configuration
 */
const defaultConfig: ILoggerConfig = {
  level: process.env.LOG_LEVEL as LogLevel || getLogLevel(),
  prettyPrint: process.env.NODE_ENV === 'development',
  colorize: process.env.NODE_ENV === 'development',
  filePath: path.join(logDir, 'notification-service.log'),
  maxFileSize: 5242880, // 5MB
  maxFiles: 5,
  console: true,
  defaultMeta: {
    service: 'notification-service',
  },
  redactPatterns: [
    /password/i,
    /secret/i,
    /token/i,
    /key/i,
    /authorization/i,
    /cookie/i,
  ],
};

/**
 * Create the logger instance with the specified configuration
 */
export const createLogger = (config: Partial<ILoggerConfig> = {}) => {
  const mergedConfig: ILoggerConfig = { ...defaultConfig, ...config };
  
  return winston.createLogger({
    level: mergedConfig.level,
    defaultMeta: mergedConfig.defaultMeta,
    transports: createTransports(mergedConfig),
    exitOnError: false,
  });
};

/**
 * Default logger instance
 */
export const logger = createLogger();

/**
 * Create a child logger with context information
 * This is useful for request tracking and correlation
 */
export const createContextLogger = (context: ILogContext) => {
  return logger.child(context);
};

/**
 * Middleware for enriching logs with request context
 * This can be used with Express middleware to add request information to logs
 */
export const requestContextMiddleware = () => {
  return (req: any, res: any, next: any) => {
    const correlationId = req.headers['x-correlation-id'] || 
                          req.headers['x-request-id'] || 
                          `req-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    // Add correlation ID to response headers for tracking
    res.setHeader('x-correlation-id', correlationId);
    
    // Create a request-scoped logger with context
    req.logger = createContextLogger({
      correlationId,
      serviceName: 'notification-service',
      timestamp: new Date().toISOString(),
      metadata: {
        method: req.method,
        path: req.path,
        ip: req.ip,
        userAgent: req.headers['user-agent'],
      },
    });
    
    next();
  };
};

export default logger;