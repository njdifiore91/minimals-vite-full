/**
 * TypeScript declaration file for environment variables used by the Notification Service.
 * Extends the NodeJS namespace to include custom environment variables for:
 * - RabbitMQ settings
 * - Webhook configurations
 * - Redis cache details
 * - Application parameters
 */

declare namespace NodeJS {
  interface ProcessEnv {
    // Node environment
    NODE_ENV: 'development' | 'production' | 'test' | 'staging';
    
    // Application settings
    PORT: string;
    LOG_LEVEL: 'error' | 'warn' | 'info' | 'http' | 'verbose' | 'debug' | 'silly';
    
    // RabbitMQ connection settings
    RABBITMQ_HOST: string;
    RABBITMQ_PORT: string;
    RABBITMQ_USERNAME: string;
    RABBITMQ_PASSWORD: string;
    RABBITMQ_VHOST?: string;
    
    // RabbitMQ exchange and queue settings
    RABBITMQ_EXCHANGE: string;
    RABBITMQ_NOTIFICATION_QUEUE: string;
    RABBITMQ_RETRY_QUEUE: string;
    RABBITMQ_DEAD_LETTER_EXCHANGE: string;
    RABBITMQ_DEAD_LETTER_QUEUE: string;
    
    // Redis cache configuration
    REDIS_HOST: string;
    REDIS_PORT: string;
    REDIS_PASSWORD?: string;
    REDIS_TLS_ENABLED: string;
    REDIS_DATA_TTL: string; // TTL for application data in seconds (default: 900 - 15 minutes)
    REDIS_SESSION_TTL: string; // TTL for session data in seconds (default: 86400 - 24 hours)
    
    // Webhook configuration
    WEBHOOK_RETRY_LIMIT: string;
    WEBHOOK_RETRY_INITIAL_INTERVAL: string; // Initial retry interval in milliseconds
    WEBHOOK_RETRY_MULTIPLIER: string; // Backoff multiplier for subsequent retries
    WEBHOOK_RETRY_MAX_INTERVAL: string; // Maximum retry interval in milliseconds
    WEBHOOK_SIGNATURE_SECRET: string; // Secret for HMAC signature generation
    
    // Email notification settings
    EMAIL_ENABLED: string;
    EMAIL_FROM: string;
    EMAIL_SMTP_HOST?: string;
    EMAIL_SMTP_PORT?: string;
    EMAIL_SMTP_USER?: string;
    EMAIL_SMTP_PASSWORD?: string;
    EMAIL_SMTP_SECURE?: string;
    
    // SMS notification settings
    SMS_ENABLED: string;
    SMS_PROVIDER?: string;
    SMS_API_KEY?: string;
    SMS_FROM_NUMBER?: string;
    
    // Push notification settings
    PUSH_ENABLED: string;
    PUSH_PROVIDER?: string;
    PUSH_API_KEY?: string;
    
    // Monitoring and observability
    ENABLE_METRICS: string;
    METRICS_PORT?: string;
  }
}