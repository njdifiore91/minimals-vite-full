/**
 * Logger Configuration
 * 
 * This file configures the logging system for the Notification Service. It defines log levels,
 * formats, transports, and context enrichment. It enables comprehensive logging for monitoring,
 * debugging, and troubleshooting the service's operation.
 */

import winston from 'winston';
import { ILoggerConfig } from '../types/config';
import { ILogContext } from '../types/common';

// Define log levels with their priorities
const logLevels = {
  error: 0,   // Processing failures
  warn: 1,    // Potential issues
  info: 2,    // Normal operations
  debug: 3,   // Troubleshooting (development only)
};

// Define log level colors for console output
const logColors = {
  error: 'red',
  warn: 'yellow',
  info: 'green',
  debug: 'blue',
};

// Add colors to Winston
winston.addColors(logColors);

/**
 * Default logger configuration
 */
const defaultConfig: ILoggerConfig = {
  level: process.env.LOG_LEVEL || 'info',
  format: process.env.NODE_ENV === 'development' ? 'pretty' : 'json',
  timestamp: true,
};

/**
 * Create a Winston logger instance with the specified configuration
 * 
 * @param config - Logger configuration options
 * @returns Configured Winston logger instance
 */
export const createLogger = (config: ILoggerConfig = defaultConfig) => {
  // Determine log level based on environment
  const level = config.level || (process.env.NODE_ENV === 'development' ? 'debug' : 'info');
  
  // Define transports based on environment
  const transports: winston.transport[] = [];
  
  // Always add console transport
  transports.push(
    new winston.transports.Console({
      level,
      format: winston.format.combine(
        winston.format.colorize({ all: true }),
        winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }),
        winston.format.printf((info) => {
          // Extract correlation ID from metadata if available
          const meta = info.metadata || {};
          const correlationId = meta.correlationId ? `[${meta.correlationId}] ` : '';
          return `${info.timestamp} ${info.level}: ${correlationId}${info.message}`;
        })
      ),
    })
  );
  
  // Add file transport in production and staging
  if (process.env.NODE_ENV === 'production' || process.env.NODE_ENV === 'staging') {
    transports.push(
      new winston.transports.File({
        filename: 'logs/notification-service.log',
        level,
        format: winston.format.combine(
          winston.format.timestamp(),
          winston.format.json()
        ),
        maxsize: 10 * 1024 * 1024, // 10MB
        maxFiles: 5,
        tailable: true,
      })
    );
    
    // Add separate error log file
    transports.push(
      new winston.transports.File({
        filename: 'logs/notification-service-error.log',
        level: 'error',
        format: winston.format.combine(
          winston.format.timestamp(),
          winston.format.json()
        ),
        maxsize: 10 * 1024 * 1024, // 10MB
        maxFiles: 5,
        tailable: true,
      })
    );
  }
  
  // Create format based on configuration
  let format: winston.Logform.Format;
  
  if (config.format === 'json' || process.env.NODE_ENV === 'production') {
    format = winston.format.combine(
      winston.format.timestamp(),
      winston.format.metadata({ fillExcept: ['message', 'level', 'timestamp'] }),
      winston.format.json()
    );
  } else {
    format = winston.format.combine(
      winston.format.colorize({ all: true }),
      winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss.SSS' }),
      winston.format.metadata({ fillExcept: ['message', 'level', 'timestamp'] }),
      winston.format.printf((info) => {
        // Extract correlation ID from metadata if available
        const meta = info.metadata || {};
        const correlationId = meta.correlationId ? `[${meta.correlationId}] ` : '';
        const metaStr = Object.keys(meta).length > 0 ? 
          `\n${JSON.stringify(meta, null, 2)}` : '';
        
        return `${info.timestamp} ${info.level}: ${correlationId}${info.message}${metaStr}`;
      })
    );
  }
  
  // Create and return the logger
  return winston.createLogger({
    levels: logLevels,
    level,
    format,
    transports,
    exitOnError: false,
  });
};

/**
 * The main logger instance for the Notification Service
 */
export const logger = createLogger();

/**
 * Create a child logger with additional context
 * 
 * @param context - Additional context to include in all logs
 * @returns Child logger instance
 */
export const createChildLogger = (context: ILogContext) => {
  return logger.child({ metadata: context });
};

/**
 * Configure the logger based on the provided configuration
 * 
 * @param config - Logger configuration options
 */
export const configureLogger = (config: ILoggerConfig) => {
  // Create a new logger with the updated configuration
  const newLogger = createLogger(config);
  
  // Replace the transports in the existing logger
  logger.clear();
  newLogger.transports.forEach(transport => logger.add(transport));
  
  // Update the log level
  logger.level = newLogger.level;
};

export default {
  logger,
  createChildLogger,
  configureLogger,
};