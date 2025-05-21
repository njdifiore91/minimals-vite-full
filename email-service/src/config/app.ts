/**
 * Core Application Configuration
 * 
 * This module defines and exports the core application configuration for the Email Service microservice.
 * It centralizes environment variables, application settings, and environment-specific configurations
 * (development, staging, production). This file is essential for maintaining consistent configuration
 * across the service and ensuring proper environment-specific behavior.
 */

import fs from 'fs';
import path from 'path';
import dotenv from 'dotenv';
import { 
  Environment, 
  IAppConfig, 
  IEnvSchema, 
  IEnvValidationResult, 
  IEnvironmentConfig,
  IServiceConfig,
  IS3Config,
  IImapConfig,
  IRabbitMQConfig,
  IExchangeConfig,
  IMessageConfig,
  ILoggingConfig
} from '../types/config';
import { ILogLevel } from '../types/common';
import { createComponentLogger } from './logger';

// Initialize logger for configuration module
const logger = createComponentLogger('AppConfig');

/**
 * Load environment variables from .env file if present
 */
function loadEnvFile(envPath?: string): void {
  const defaultEnvPath = path.resolve(process.cwd(), '.env');
  const envFilePath = envPath || defaultEnvPath;
  
  if (fs.existsSync(envFilePath)) {
    logger.info(`Loading environment variables from ${envFilePath}`);
    dotenv.config({ path: envFilePath });
  } else {
    logger.info('No .env file found, using process environment variables');
  }
}

/**
 * Environment variable schema for validation
 * 
 * This schema defines the required environment variables and their validation rules.
 * It is used to validate the environment variables at service startup to ensure
 * all required configuration is present and valid.
 */
const envSchema: Record<string, IEnvSchema> = {
  // Node environment
  NODE_ENV: {
    name: 'NODE_ENV',
    required: false,
    default: 'development',
    validate: (value) => ['development', 'production', 'staging', 'test'].includes(value),
    errorMessage: 'NODE_ENV must be one of: development, production, staging, test'
  },
  
  // Application settings
  APP_NAME: {
    name: 'APP_NAME',
    required: false,
    default: 'email-service'
  },
  APP_VERSION: {
    name: 'APP_VERSION',
    required: false,
    default: '1.0.0'
  },
  PORT: {
    name: 'PORT',
    required: false,
    default: '3000',
    validate: (value) => !isNaN(parseInt(value, 10)),
    errorMessage: 'PORT must be a valid number'
  },
  LOG_LEVEL: {
    name: 'LOG_LEVEL',
    required: false,
    default: 'info',
    validate: (value) => ['error', 'warn', 'info', 'debug'].includes(value.toLowerCase()),
    errorMessage: 'LOG_LEVEL must be one of: error, warn, info, debug'
  },
  EMAIL_POLLING_INTERVAL: {
    name: 'EMAIL_POLLING_INTERVAL',
    required: false,
    default: '60000', // 1 minute
    validate: (value) => !isNaN(parseInt(value, 10)) && parseInt(value, 10) > 0,
    errorMessage: 'EMAIL_POLLING_INTERVAL must be a positive number'
  },
  
  // IMAP connection settings
  IMAP_HOST: {
    name: 'IMAP_HOST',
    required: true,
    errorMessage: 'IMAP_HOST is required'
  },
  IMAP_PORT: {
    name: 'IMAP_PORT',
    required: true,
    validate: (value) => !isNaN(parseInt(value, 10)),
    errorMessage: 'IMAP_PORT must be a valid number'
  },
  IMAP_USER: {
    name: 'IMAP_USER',
    required: true,
    errorMessage: 'IMAP_USER is required'
  },
  IMAP_PASSWORD: {
    name: 'IMAP_PASSWORD',
    required: true,
    errorMessage: 'IMAP_PASSWORD is required'
  },
  IMAP_TLS_ENABLED: {
    name: 'IMAP_TLS_ENABLED',
    required: false,
    default: 'true',
    validate: (value) => ['true', 'false'].includes(value.toLowerCase()),
    errorMessage: 'IMAP_TLS_ENABLED must be either true or false'
  },
  IMAP_TLS_REJECT_UNAUTHORIZED: {
    name: 'IMAP_TLS_REJECT_UNAUTHORIZED',
    required: false,
    default: 'true',
    validate: (value) => ['true', 'false'].includes(value.toLowerCase()),
    errorMessage: 'IMAP_TLS_REJECT_UNAUTHORIZED must be either true or false'
  },
  
  // RabbitMQ connection settings
  RABBITMQ_HOST: {
    name: 'RABBITMQ_HOST',
    required: true,
    errorMessage: 'RABBITMQ_HOST is required'
  },
  RABBITMQ_PORT: {
    name: 'RABBITMQ_PORT',
    required: true,
    validate: (value) => !isNaN(parseInt(value, 10)),
    errorMessage: 'RABBITMQ_PORT must be a valid number'
  },
  RABBITMQ_USER: {
    name: 'RABBITMQ_USER',
    required: true,
    errorMessage: 'RABBITMQ_USER is required'
  },
  RABBITMQ_PASSWORD: {
    name: 'RABBITMQ_PASSWORD',
    required: true,
    errorMessage: 'RABBITMQ_PASSWORD is required'
  },
  RABBITMQ_VHOST: {
    name: 'RABBITMQ_VHOST',
    required: false,
    default: '/'
  },
  RABBITMQ_EXCHANGE: {
    name: 'RABBITMQ_EXCHANGE',
    required: false,
    default: 'mca.documents'
  },
  RABBITMQ_EXCHANGE_TYPE: {
    name: 'RABBITMQ_EXCHANGE_TYPE',
    required: false,
    default: 'fanout',
    validate: (value) => ['direct', 'fanout', 'topic', 'headers'].includes(value),
    errorMessage: 'RABBITMQ_EXCHANGE_TYPE must be one of: direct, fanout, topic, headers'
  },
  RABBITMQ_TLS_ENABLED: {
    name: 'RABBITMQ_TLS_ENABLED',
    required: false,
    default: 'true',
    validate: (value) => ['true', 'false'].includes(value.toLowerCase()),
    errorMessage: 'RABBITMQ_TLS_ENABLED must be either true or false'
  },
  
  // S3 storage configuration
  S3_ENDPOINT: {
    name: 'S3_ENDPOINT',
    required: true,
    errorMessage: 'S3_ENDPOINT is required'
  },
  S3_REGION: {
    name: 'S3_REGION',
    required: true,
    errorMessage: 'S3_REGION is required'
  },
  S3_ACCESS_KEY: {
    name: 'S3_ACCESS_KEY',
    required: true,
    errorMessage: 'S3_ACCESS_KEY is required'
  },
  S3_SECRET_KEY: {
    name: 'S3_SECRET_KEY',
    required: true,
    errorMessage: 'S3_SECRET_KEY is required'
  },
  S3_BUCKET: {
    name: 'S3_BUCKET',
    required: false,
    default: 'mca-documents-development'
  },
  S3_USE_SSL: {
    name: 'S3_USE_SSL',
    required: false,
    default: 'true',
    validate: (value) => ['true', 'false'].includes(value.toLowerCase()),
    errorMessage: 'S3_USE_SSL must be either true or false'
  },
  S3_ENCRYPTION_ENABLED: {
    name: 'S3_ENCRYPTION_ENABLED',
    required: false,
    default: 'true',
    validate: (value) => ['true', 'false'].includes(value.toLowerCase()),
    errorMessage: 'S3_ENCRYPTION_ENABLED must be either true or false'
  }
};

/**
 * Validate environment variables against schema
 * 
 * @param schema - Environment variable schema
 * @returns Validation result with errors and validated environment
 */
function validateEnv(schema: Record<string, IEnvSchema>): IEnvValidationResult {
  const result: IEnvValidationResult = {
    isValid: true,
    errors: [],
    env: {}
  };
  
  // Check each schema entry against environment
  Object.values(schema).forEach((entry) => {
    const { name, required, default: defaultValue, validate, errorMessage } = entry;
    let value = process.env[name];
    
    // If value is not provided but required
    if (!value && required) {
      result.isValid = false;
      result.errors.push(errorMessage || `${name} is required`);
      return;
    }
    
    // If value is not provided but has default
    if (!value && defaultValue !== undefined) {
      value = defaultValue;
    }
    
    // If value is provided and has validation function
    if (value && validate && !validate(value)) {
      result.isValid = false;
      result.errors.push(errorMessage || `${name} has invalid value: ${value}`);
      return;
    }
    
    // Store validated value
    if (value) {
      result.env[name] = value;
    }
  });
  
  return result;
}

/**
 * Get the current environment
 * 
 * @returns The current environment (development, staging, production)
 */
function getEnvironment(): Environment {
  const nodeEnv = process.env.NODE_ENV || 'development';
  
  switch (nodeEnv) {
    case 'production':
      return 'production';
    case 'staging':
      return 'staging';
    case 'development':
    default:
      return 'development';
  }
}

/**
 * Create application configuration
 * 
 * @returns Application configuration
 */
function createAppConfig(): IAppConfig {
  return {
    serviceName: process.env.APP_NAME || 'email-service',
    version: process.env.APP_VERSION || '1.0.0',
    port: parseInt(process.env.PORT || '3000', 10),
    environment: getEnvironment(),
    nodeEnv: process.env.NODE_ENV || 'development',
    debug: process.env.DEBUG === 'true'
  };
}

/**
 * Create S3 configuration
 * 
 * @returns S3 configuration
 */
function createS3Config(): IS3Config {
  return {
    endpoint: process.env.S3_ENDPOINT || '',
    forcePathStyle: process.env.S3_FORCE_PATH_STYLE === 'true',
    region: process.env.S3_REGION || 'us-east-1',
    accessKey: process.env.S3_ACCESS_KEY || '',
    secretKey: process.env.S3_SECRET_KEY || '',
    productionBucket: 'mca-documents-production',
    stagingBucket: 'mca-documents-staging',
    developmentBucket: process.env.S3_BUCKET || 'mca-documents-development',
    sslEnabled: process.env.S3_USE_SSL !== 'false',
    connectionTimeout: parseInt(process.env.S3_UPLOAD_TIMEOUT || '30000', 10),
    maxRetries: parseInt(process.env.MAX_RETRY_ATTEMPTS || '3', 10),
    useEncryption: process.env.S3_ENCRYPTION_ENABLED !== 'false'
  };
}

/**
 * Create IMAP configuration
 * 
 * @returns IMAP configuration
 */
function createImapConfig(): IImapConfig {
  return {
    host: process.env.IMAP_HOST || '',
    port: parseInt(process.env.IMAP_PORT || '993', 10),
    tls: process.env.IMAP_TLS_ENABLED !== 'false',
    tlsOptions: {
      required: true,
      minVersion: 'TLSv1.2',
      rejectUnauthorized: process.env.IMAP_TLS_REJECT_UNAUTHORIZED !== 'false'
    },
    user: process.env.IMAP_USER || '',
    password: process.env.IMAP_PASSWORD || '',
    mailbox: process.env.IMAP_MAILBOX || 'INBOX',
    pollingInterval: parseInt(process.env.EMAIL_POLLING_INTERVAL || '60000', 10),
    connectionTimeout: parseInt(process.env.IMAP_CONNECTION_TIMEOUT || '30000', 10),
    idleTimeout: parseInt(process.env.IMAP_IDLE_TIMEOUT || '300000', 10),
    maxRetries: parseInt(process.env.MAX_RETRY_ATTEMPTS || '5', 10),
    retryDelay: parseInt(process.env.RETRY_INITIAL_DELAY || '5000', 10)
  };
}

/**
 * Create RabbitMQ configuration
 * 
 * @returns RabbitMQ configuration
 */
function createRabbitMQConfig(): IRabbitMQConfig {
  return {
    host: process.env.RABBITMQ_HOST || '',
    port: parseInt(process.env.RABBITMQ_PORT || '5672', 10),
    vhost: process.env.RABBITMQ_VHOST || '/',
    username: process.env.RABBITMQ_USER || '',
    password: process.env.RABBITMQ_PASSWORD || '',
    useTls: process.env.RABBITMQ_TLS_ENABLED !== 'false',
    connectionTimeout: parseInt(process.env.RABBITMQ_CONNECTION_TIMEOUT || '30000', 10),
    heartbeat: parseInt(process.env.RABBITMQ_HEARTBEAT || '60', 10),
    maxRetries: parseInt(process.env.MAX_RETRY_ATTEMPTS || '5', 10),
    retryDelay: parseInt(process.env.RETRY_INITIAL_DELAY || '5000', 10)
  };
}

/**
 * Create RabbitMQ exchange configuration
 * 
 * @returns Exchange configuration
 */
function createExchangeConfig(): IExchangeConfig {
  return {
    name: process.env.RABBITMQ_EXCHANGE || 'mca.documents',
    type: (process.env.RABBITMQ_EXCHANGE_TYPE || 'fanout') as 'direct' | 'fanout' | 'topic' | 'headers',
    durable: true,
    autoDelete: false
  };
}

/**
 * Create RabbitMQ message configuration
 * 
 * @returns Message configuration
 */
function createMessageConfig(): IMessageConfig {
  return {
    contentType: 'application/json',
    contentEncoding: 'utf-8',
    deliveryMode: 2 as 1 | 2, // Persistent
    priority: 0,
    usePublisherConfirms: true
  };
}

/**
 * Create logging configuration
 * 
 * @returns Logging configuration
 */
function createLoggingConfig(): ILoggingConfig {
  const logLevel = (process.env.LOG_LEVEL || 'info').toUpperCase() as ILogLevel;
  
  return {
    level: logLevel,
    prettyPrint: process.env.NODE_ENV !== 'production',
    timestamp: true,
    colorize: process.env.NODE_ENV !== 'production',
    logToFile: process.env.NODE_ENV === 'production',
    logFilePath: process.env.LOG_DIR ? path.join(process.env.LOG_DIR, 'email-service.log') : undefined,
    maxLogFileSize: 10485760, // 10MB
    maxLogFiles: 10
  };
}

/**
 * Create environment-specific configuration
 * 
 * @returns Environment-specific configuration
 */
function createEnvironmentConfig(): IEnvironmentConfig {
  return {
    imap: createImapConfig(),
    rabbitmq: createRabbitMQConfig(),
    exchange: createExchangeConfig(),
    message: createMessageConfig(),
    s3: createS3Config(),
    logging: createLoggingConfig()
  };
}

/**
 * Initialize configuration
 * 
 * This function loads environment variables, validates them against the schema,
 * and creates the application configuration. It throws an error if validation fails.
 * 
 * @param options - Configuration loading options
 * @returns Service configuration
 */
export function initConfig(options: { envPath?: string, throwOnError?: boolean } = {}): IServiceConfig {
  // Load environment variables from .env file if present
  loadEnvFile(options.envPath);
  
  // Validate environment variables
  const validationResult = validateEnv(envSchema);
  
  // Log validation errors
  if (!validationResult.isValid) {
    logger.error('Environment validation failed', { errors: validationResult.errors });
    
    if (options.throwOnError !== false) {
      throw new Error(`Configuration validation failed: ${validationResult.errors.join(', ')}`);
    }
  }
  
  // Create configuration
  return {
    app: createAppConfig(),
    env: createEnvironmentConfig()
  };
}

/**
 * Application configuration
 * 
 * This is the main configuration object that should be imported and used throughout the application.
 */
export const appConfig = initConfig({ throwOnError: false });

/**
 * Export default configuration
 */
export default appConfig;