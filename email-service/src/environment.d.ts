/**
 * TypeScript declaration file for Email Service environment variables.
 * Extends the NodeJS namespace to include custom environment variables
 * for IMAP configuration, RabbitMQ settings, S3 storage details, and application parameters.
 */

declare namespace NodeJS {
  interface ProcessEnv {
    // Node environment
    NODE_ENV: 'development' | 'production' | 'staging' | 'test';
    
    // Application settings
    APP_NAME: string;
    APP_VERSION: string;
    PORT: string;
    LOG_LEVEL: 'error' | 'warn' | 'info' | 'debug';
    EMAIL_POLLING_INTERVAL: string; // in milliseconds
    
    // IMAP connection settings
    IMAP_HOST: string;
    IMAP_PORT: string;
    IMAP_USER: string;
    IMAP_PASSWORD: string;
    IMAP_TLS_ENABLED: string; // 'true' or 'false'
    IMAP_TLS_REJECT_UNAUTHORIZED: string; // 'true' or 'false'
    IMAP_MAILBOX: string; // e.g., 'INBOX'
    IMAP_SEARCH_CRITERIA: string; // JSON string of search criteria
    IMAP_CONNECTION_TIMEOUT: string; // in milliseconds
    IMAP_IDLE_TIMEOUT: string; // in milliseconds
    
    // RabbitMQ connection settings
    RABBITMQ_HOST: string;
    RABBITMQ_PORT: string;
    RABBITMQ_USER: string;
    RABBITMQ_PASSWORD: string;
    RABBITMQ_VHOST: string;
    RABBITMQ_EXCHANGE: string; // e.g., 'mca.documents'
    RABBITMQ_EXCHANGE_TYPE: string; // e.g., 'fanout'
    RABBITMQ_ROUTING_KEY: string; // e.g., 'document.new'
    RABBITMQ_TLS_ENABLED: string; // 'true' or 'false'
    RABBITMQ_TLS_CERT_PATH: string;
    RABBITMQ_TLS_KEY_PATH: string;
    RABBITMQ_TLS_CA_PATH: string;
    RABBITMQ_HEARTBEAT: string; // in seconds
    RABBITMQ_CONNECTION_TIMEOUT: string; // in milliseconds
    
    // S3 storage configuration
    S3_ENDPOINT: string;
    S3_REGION: string;
    S3_ACCESS_KEY: string;
    S3_SECRET_KEY: string;
    S3_BUCKET: string; // e.g., 'mca-documents-production' or 'mca-documents-staging'
    S3_USE_SSL: string; // 'true' or 'false'
    S3_FORCE_PATH_STYLE: string; // 'true' or 'false'
    S3_ENCRYPTION_ENABLED: string; // 'true' or 'false', for AES-256 encryption
    S3_UPLOAD_TIMEOUT: string; // in milliseconds
    S3_DOWNLOAD_TIMEOUT: string; // in milliseconds
    
    // Document processing settings
    MAX_ATTACHMENT_SIZE: string; // in bytes
    ALLOWED_MIME_TYPES: string; // comma-separated list, e.g., 'application/pdf,image/tiff,image/png,image/jpeg'
    VIRUS_SCAN_ENABLED: string; // 'true' or 'false'
    VIRUS_SCAN_ENDPOINT: string; // URL of virus scanning service
    
    // Retry and error handling settings
    MAX_RETRY_ATTEMPTS: string;
    RETRY_INITIAL_DELAY: string; // in milliseconds
    RETRY_MAX_DELAY: string; // in milliseconds
    RETRY_BACKOFF_FACTOR: string; // multiplier for exponential backoff
    
    // Monitoring and observability
    ENABLE_METRICS: string; // 'true' or 'false'
    METRICS_PORT: string;
    CORRELATION_ID_HEADER: string; // for distributed tracing
  }
}