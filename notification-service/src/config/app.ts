/**
 * Application Configuration for Notification Service
 *
 * This file defines and exports the core application configuration for the Notification Service microservice.
 * It centralizes environment variables, application settings, and environment-specific configurations
 * (development, staging, production). This file is essential for maintaining consistent configuration
 * across the service and ensuring proper environment-specific behavior.
 */

import path from 'path';
import { IConfig, Environment, LogLevel } from '../types/config';

/**
 * Package information from package.json
 */
const packageInfo = {
  name: process.env.npm_package_name || 'notification-service',
  version: process.env.npm_package_version || '1.0.0',
};

/**
 * Helper function to get environment variables with validation
 * @param key Environment variable key
 * @param defaultValue Optional default value if environment variable is not set
 * @param required Whether the environment variable is required
 * @returns The environment variable value or default value
 * @throws Error if required environment variable is not set
 */
export const getEnv = (key: string, defaultValue?: string, required: boolean = false): string => {
  const value = process.env[key] || defaultValue;
  
  if (required && value === undefined) {
    throw new Error(`Required environment variable ${key} is not set`);
  }
  
  return value as string;
};

/**
 * Helper function to get numeric environment variables with validation
 * @param key Environment variable key
 * @param defaultValue Optional default value if environment variable is not set
 * @param required Whether the environment variable is required
 * @returns The environment variable value as a number or default value
 * @throws Error if required environment variable is not set or not a valid number
 */
export const getNumericEnv = (key: string, defaultValue?: number, required: boolean = false): number => {
  const stringValue = getEnv(key, defaultValue?.toString(), required);
  
  if (stringValue === undefined) {
    return defaultValue as number;
  }
  
  const numericValue = Number(stringValue);
  
  if (isNaN(numericValue)) {
    throw new Error(`Environment variable ${key} is not a valid number: ${stringValue}`);
  }
  
  return numericValue;
};

/**
 * Helper function to get boolean environment variables with validation
 * @param key Environment variable key
 * @param defaultValue Optional default value if environment variable is not set
 * @returns The environment variable value as a boolean or default value
 */
export const getBooleanEnv = (key: string, defaultValue: boolean = false): boolean => {
  const stringValue = getEnv(key, defaultValue.toString(), false);
  
  if (stringValue === undefined) {
    return defaultValue;
  }
  
  return stringValue.toLowerCase() === 'true';
};

/**
 * Helper function to get array environment variables with validation
 * @param key Environment variable key
 * @param defaultValue Optional default value if environment variable is not set
 * @param delimiter Delimiter to split the environment variable value (default: ',')
 * @returns The environment variable value as an array or default value
 */
export const getArrayEnv = (key: string, defaultValue: string[] = [], delimiter: string = ','): string[] => {
  const stringValue = getEnv(key, defaultValue.join(delimiter), false);
  
  if (stringValue === undefined || stringValue === '') {
    return defaultValue;
  }
  
  return stringValue.split(delimiter).map(item => item.trim());
};

/**
 * Helper function to get the current environment
 * @returns The current environment (development, staging, production, test)
 */
export const getEnvironment = (): Environment => {
  const env = getEnv('NODE_ENV', 'development');
  
  switch (env) {
    case 'development':
      return Environment.DEVELOPMENT;
    case 'staging':
      return Environment.STAGING;
    case 'production':
      return Environment.PRODUCTION;
    case 'test':
      return Environment.TEST;
    default:
      return Environment.DEVELOPMENT;
  }
};

/**
 * Helper function to get the log level based on environment
 * @returns The appropriate log level for the current environment
 */
export const getLogLevel = (): LogLevel => {
  const configuredLevel = getEnv('LOG_LEVEL');
  
  if (configuredLevel) {
    switch (configuredLevel.toLowerCase()) {
      case 'error':
        return LogLevel.ERROR;
      case 'warn':
        return LogLevel.WARN;
      case 'info':
        return LogLevel.INFO;
      case 'debug':
        return LogLevel.DEBUG;
      default:
        break;
    }
  }
  
  // Default log levels based on environment if not explicitly configured
  const env = getEnvironment();
  
  switch (env) {
    case Environment.DEVELOPMENT:
      return LogLevel.DEBUG;
    case Environment.TEST:
      return LogLevel.WARN;
    case Environment.STAGING:
      return LogLevel.INFO;
    case Environment.PRODUCTION:
      return LogLevel.INFO;
    default:
      return LogLevel.INFO;
  }
};

/**
 * Main configuration object for the Notification Service
 */
export const config: IConfig = {
  // Application configuration
  app: {
    name: packageInfo.name,
    version: packageInfo.version,
    environment: getEnvironment(),
    port: getNumericEnv('PORT', 3000),
    baseUrl: getEnv('BASE_URL', 'http://localhost:3000'),
    correlationIdHeader: getEnv('CORRELATION_ID_HEADER', 'x-correlation-id'),
    enableRequestLogging: getBooleanEnv('ENABLE_REQUEST_LOGGING', true),
    enableCompression: getBooleanEnv('ENABLE_COMPRESSION', true),
    maxBodySize: getEnv('MAX_BODY_SIZE', '1mb'),
    requestTimeout: getNumericEnv('REQUEST_TIMEOUT', 30000), // 30 seconds
    cors: {
      enabled: getBooleanEnv('CORS_ENABLED', true),
      origin: getEnv('CORS_ORIGIN', '*'),
      methods: getArrayEnv('CORS_METHODS', ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']),
      allowedHeaders: getArrayEnv('CORS_ALLOWED_HEADERS', [
        'Content-Type',
        'Authorization',
        'X-Requested-With',
        'Accept',
        'Origin',
        'x-correlation-id',
      ]),
      exposedHeaders: getArrayEnv('CORS_EXPOSED_HEADERS', ['x-correlation-id']),
      credentials: getBooleanEnv('CORS_CREDENTIALS', true),
      maxAge: getNumericEnv('CORS_MAX_AGE', 86400), // 24 hours
    },
  },
  
  // Logger configuration
  logger: {
    level: getLogLevel(),
    prettyPrint: getEnvironment() === Environment.DEVELOPMENT,
    colorize: getEnvironment() === Environment.DEVELOPMENT,
    filePath: getEnv('LOG_FILE_PATH', path.join(process.cwd(), 'logs', 'notification-service.log')),
    maxFileSize: getNumericEnv('LOG_MAX_FILE_SIZE', 5242880), // 5MB
    maxFiles: getNumericEnv('LOG_MAX_FILES', 5),
    console: getBooleanEnv('LOG_CONSOLE', true),
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
  },
  
  // Redis configuration
  redis: {
    host: getEnv('REDIS_HOST', 'localhost', true),
    port: getNumericEnv('REDIS_PORT', 6379),
    password: getEnv('REDIS_PASSWORD'),
    db: getNumericEnv('REDIS_DB', 0),
    tls: getBooleanEnv('REDIS_TLS_ENABLED', false),
    tlsCA: getEnv('REDIS_TLS_CA'),
    tlsCert: getEnv('REDIS_TLS_CERT'),
    tlsKey: getEnv('REDIS_TLS_KEY'),
    connectTimeout: getNumericEnv('REDIS_CONNECT_TIMEOUT', 10000),
    commandTimeout: getNumericEnv('REDIS_COMMAND_TIMEOUT', 5000),
    autoReconnect: getBooleanEnv('REDIS_AUTO_RECONNECT', true),
    maxReconnectAttempts: getNumericEnv('REDIS_MAX_RECONNECT_ATTEMPTS', 10),
    reconnectInterval: getNumericEnv('REDIS_RECONNECT_INTERVAL', 1000),
    cluster: getBooleanEnv('REDIS_CLUSTER_ENABLED', false),
    clusterNodes: getEnv('REDIS_CLUSTER_NODES') ? 
      getArrayEnv('REDIS_CLUSTER_NODES').map(node => {
        const [host, port] = node.split(':');
        return { host, port: parseInt(port, 10) };
      }) : undefined,
    keyPrefix: getEnv('REDIS_KEY_PREFIX', 'notification:'),
    defaultDataTTL: getNumericEnv('REDIS_DATA_TTL', 900), // 15 minutes
    defaultSessionTTL: getNumericEnv('REDIS_SESSION_TTL', 86400), // 24 hours
    enableRateLimiter: getBooleanEnv('REDIS_ENABLE_RATE_LIMITER', true),
    maxConnections: getNumericEnv('REDIS_MAX_CONNECTIONS', 50),
  },
  
  // Webhook configuration
  webhook: {
    defaultTimeout: getNumericEnv('WEBHOOK_TIMEOUT', 10000), // 10 seconds
    maxPayloadSize: getNumericEnv('WEBHOOK_MAX_PAYLOAD_SIZE', 1048576), // 1MB
    enableSignature: getBooleanEnv('WEBHOOK_ENABLE_SIGNATURE', true),
    signatureAlgorithm: getEnv('WEBHOOK_SIGNATURE_ALGORITHM', 'sha256'),
    signatureHeader: getEnv('WEBHOOK_SIGNATURE_HEADER', 'X-Webhook-Signature'),
    validatePayload: getBooleanEnv('WEBHOOK_VALIDATE_PAYLOAD', true),
    defaultEndpoint: getEnv('WEBHOOK_DEFAULT_ENDPOINT'),
    enableBatching: getBooleanEnv('WEBHOOK_ENABLE_BATCHING', false),
    maxBatchSize: getNumericEnv('WEBHOOK_MAX_BATCH_SIZE', 10),
    batchInterval: getNumericEnv('WEBHOOK_BATCH_INTERVAL', 1000), // 1 second
    enableMetrics: getBooleanEnv('WEBHOOK_ENABLE_METRICS', true),
    enableLogging: getBooleanEnv('WEBHOOK_ENABLE_LOGGING', true),
    defaultHeaders: {
      'Content-Type': 'application/json',
      'User-Agent': `DollarFunding-Webhook-Service/${packageInfo.version}`,
    },
  },
  
  // RabbitMQ configuration
  rabbitmq: {
    uri: `${getBooleanEnv('RABBITMQ_TLS_ENABLED', false) ? 'amqps' : 'amqp'}://${getEnv('RABBITMQ_USERNAME', 'guest')}:${getEnv('RABBITMQ_PASSWORD', 'guest')}@${getEnv('RABBITMQ_HOST', 'localhost', true)}:${getNumericEnv('RABBITMQ_PORT', 5672)}${getEnv('RABBITMQ_VHOST', '/') !== '/' ? `/${getEnv('RABBITMQ_VHOST', '/')}` : ''}`,
    host: getEnv('RABBITMQ_HOST', 'localhost', true),
    port: getNumericEnv('RABBITMQ_PORT', 5672),
    vhost: getEnv('RABBITMQ_VHOST', '/'),
    username: getEnv('RABBITMQ_USERNAME', 'guest'),
    password: getEnv('RABBITMQ_PASSWORD', 'guest'),
    tls: getBooleanEnv('RABBITMQ_TLS_ENABLED', false),
    tlsCA: getEnv('RABBITMQ_TLS_CA'),
    tlsCert: getEnv('RABBITMQ_TLS_CERT'),
    tlsKey: getEnv('RABBITMQ_TLS_KEY'),
    connectTimeout: getNumericEnv('RABBITMQ_CONNECT_TIMEOUT', 30000),
    heartbeat: getNumericEnv('RABBITMQ_HEARTBEAT', 60),
    autoReconnect: getBooleanEnv('RABBITMQ_AUTO_RECONNECT', true),
    maxReconnectAttempts: getNumericEnv('RABBITMQ_MAX_RECONNECT_ATTEMPTS', 10),
    reconnectInterval: getNumericEnv('RABBITMQ_RECONNECT_INTERVAL', 5000),
    exchange: getEnv('RABBITMQ_EXCHANGE', 'mca.documents'),
    exchangeType: getEnv('RABBITMQ_EXCHANGE_TYPE', 'fanout'),
    exchangeDurable: getBooleanEnv('RABBITMQ_EXCHANGE_DURABLE', true),
    queue: getEnv('RABBITMQ_NOTIFICATION_QUEUE', 'notification'),
    queueDurable: getBooleanEnv('RABBITMQ_QUEUE_DURABLE', true),
    routingKey: getEnv('RABBITMQ_ROUTING_KEY', ''),
    ackMode: getEnv('RABBITMQ_ACK_MODE', 'manual') as 'auto' | 'manual',
    prefetchCount: getNumericEnv('RABBITMQ_PREFETCH_COUNT', 10),
    deadLetterExchange: getEnv('RABBITMQ_DEAD_LETTER_EXCHANGE', 'mca.deadletter'),
    deadLetterRoutingKey: getEnv('RABBITMQ_DEAD_LETTER_QUEUE', 'notification.deadletter'),
    messageTTL: getNumericEnv('RABBITMQ_MESSAGE_TTL', 604800000), // 7 days in milliseconds
    persistentMessages: getBooleanEnv('RABBITMQ_PERSISTENT_MESSAGES', true),
  },
  
  // Notification configuration
  notification: {
    defaultType: getEnv('NOTIFICATION_DEFAULT_TYPE', 'webhook'),
    defaultPriority: getEnv('NOTIFICATION_DEFAULT_PRIORITY', 'normal'),
    enableEmail: getBooleanEnv('EMAIL_ENABLED', false),
    enableSMS: getBooleanEnv('SMS_ENABLED', false),
    enablePush: getBooleanEnv('PUSH_ENABLED', false),
    enableWebhook: getBooleanEnv('WEBHOOK_ENABLED', true),
    defaultEmailSender: getEnv('EMAIL_FROM'),
    defaultSMSSender: getEnv('SMS_FROM_NUMBER'),
    defaultPushTitle: getEnv('PUSH_DEFAULT_TITLE', 'Notification'),
    enableBatching: getBooleanEnv('NOTIFICATION_ENABLE_BATCHING', false),
    maxBatchSize: getNumericEnv('NOTIFICATION_MAX_BATCH_SIZE', 10),
    batchInterval: getNumericEnv('NOTIFICATION_BATCH_INTERVAL', 1000), // 1 second
    enableMetrics: getBooleanEnv('ENABLE_METRICS', true),
    enableLogging: getBooleanEnv('NOTIFICATION_ENABLE_LOGGING', true),
    templateDir: getEnv('NOTIFICATION_TEMPLATE_DIR', path.join(process.cwd(), 'templates')),
  },
  
  // Retry configuration
  retry: {
    enabled: getBooleanEnv('RETRY_ENABLED', true),
    maxAttempts: getNumericEnv('WEBHOOK_RETRY_LIMIT', 5),
    initialDelay: getNumericEnv('WEBHOOK_RETRY_INITIAL_INTERVAL', 1000), // 1 second
    maxDelay: getNumericEnv('WEBHOOK_RETRY_MAX_INTERVAL', 60000), // 1 minute
    backoffMultiplier: getNumericEnv('WEBHOOK_RETRY_MULTIPLIER', 2),
    enableJitter: getBooleanEnv('WEBHOOK_RETRY_JITTER', true),
    retryStatusCodes: getArrayEnv('WEBHOOK_RETRY_STATUS_CODES', ['408', '429', '500', '502', '503', '504']).map(code => parseInt(code, 10)),
    retryErrorTypes: getArrayEnv('WEBHOOK_RETRY_ERROR_TYPES', ['ECONNRESET', 'ECONNREFUSED', 'ETIMEDOUT', 'ENOTFOUND']),
    enableLogging: getBooleanEnv('WEBHOOK_RETRY_LOGGING', true),
  },
};

/**
 * Validate the configuration
 * @throws Error if configuration is invalid
 */
export const validateConfig = (): void => {
  // Validate required environment variables
  const requiredEnvVars = [
    'RABBITMQ_HOST',
    'REDIS_HOST',
  ];
  
  for (const envVar of requiredEnvVars) {
    if (!process.env[envVar]) {
      throw new Error(`Required environment variable ${envVar} is not set`);
    }
  }
  
  // Validate webhook configuration if enabled
  if (config.notification.enableWebhook) {
    if (config.webhook.enableSignature && !process.env.WEBHOOK_SIGNATURE_SECRET) {
      throw new Error('WEBHOOK_SIGNATURE_SECRET is required when webhook signatures are enabled');
    }
  }
  
  // Validate email configuration if enabled
  if (config.notification.enableEmail) {
    const requiredEmailVars = [
      'EMAIL_FROM',
      'EMAIL_SMTP_HOST',
      'EMAIL_SMTP_PORT',
    ];
    
    for (const envVar of requiredEmailVars) {
      if (!process.env[envVar]) {
        throw new Error(`Required environment variable ${envVar} is not set for email notifications`);
      }
    }
  }
  
  // Validate SMS configuration if enabled
  if (config.notification.enableSMS) {
    const requiredSMSVars = [
      'SMS_API_KEY',
      'SMS_FROM_NUMBER',
    ];
    
    for (const envVar of requiredSMSVars) {
      if (!process.env[envVar]) {
        throw new Error(`Required environment variable ${envVar} is not set for SMS notifications`);
      }
    }
  }
  
  // Validate push notification configuration if enabled
  if (config.notification.enablePush) {
    const requiredPushVars = [
      'PUSH_API_KEY',
      'PUSH_PROVIDER',
    ];
    
    for (const envVar of requiredPushVars) {
      if (!process.env[envVar]) {
        throw new Error(`Required environment variable ${envVar} is not set for push notifications`);
      }
    }
  }
};

// Validate configuration on module load
try {
  validateConfig();
} catch (error) {
  // Log error but don't crash - allow application to handle this gracefully
  console.error('Configuration validation error:', error.message);
}

export default config;