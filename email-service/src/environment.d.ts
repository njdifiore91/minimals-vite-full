/**
 * TypeScript declaration file for Email Service environment variables
 * 
 * This file extends the NodeJS namespace to include custom environment variables
 * used by the Email Service for IMAP configuration, RabbitMQ settings, S3 storage
 * details, and application parameters.
 */

declare namespace NodeJS {
  interface ProcessEnv {
    // Node environment
    NODE_ENV: 'development' | 'staging' | 'production';
    
    // Application settings
    APP_NAME: string;
    APP_VERSION: string;
    PORT: string;
    LOG_LEVEL: 'error' | 'warn' | 'info' | 'debug';
    EMAIL_POLLING_INTERVAL_MS: string; // Polling interval in milliseconds
    
    // IMAP connection parameters
    IMAP_SERVER: string;
    IMAP_PORT: string;
    IMAP_USER: string;
    IMAP_PASSWORD: string;
    IMAP_TLS_ENABLED: string; // 'true' or 'false'
    IMAP_REJECT_UNAUTHORIZED: string; // 'true' or 'false' - whether to reject unauthorized TLS certificates
    IMAP_MAILBOX: string; // Mailbox to monitor (e.g., 'INBOX')
    IMAP_SEARCH_CRITERIA: string; // IMAP search criteria (e.g., 'UNSEEN')
    
    // RabbitMQ connection details
    RABBITMQ_HOST: string;
    RABBITMQ_PORT: string;
    RABBITMQ_USER: string;
    RABBITMQ_PASSWORD: string;
    RABBITMQ_VHOST: string;
    RABBITMQ_EXCHANGE: string; // 'mca.documents'
    RABBITMQ_QUEUE: string; // 'document-processing'
    RABBITMQ_TLS_ENABLED: string; // 'true' or 'false'
    RABBITMQ_CERT_PATH: string; // Path to client certificate for TLS
    RABBITMQ_KEY_PATH: string; // Path to client key for TLS
    RABBITMQ_CA_PATH: string; // Path to CA certificate for TLS
    
    // S3 storage configuration
    S3_ENDPOINT: string;
    S3_REGION: string;
    S3_BUCKET: string; // 'mca-documents-production' or 'mca-documents-staging'
    S3_ACCESS_KEY: string;
    S3_SECRET_KEY: string;
    S3_USE_SSL: string; // 'true' or 'false'
    S3_FORCE_PATH_STYLE: string; // 'true' or 'false' - whether to force path style URLs
    S3_ENCRYPTION_ENABLED: string; // 'true' or 'false' - whether to enable AES-256 encryption
    S3_UPLOAD_TIMEOUT_MS: string; // Timeout for upload operations in milliseconds
    
    // Email processing settings
    MAX_ATTACHMENT_SIZE_MB: string; // Maximum attachment size in MB
    ALLOWED_ATTACHMENT_TYPES: string; // Comma-separated list of allowed MIME types
    ATTACHMENT_STORAGE_PATH: string; // Path in S3 bucket for storing attachments
    
    // Retry and error handling settings
    MAX_RETRY_ATTEMPTS: string; // Maximum number of retry attempts for failed operations
    RETRY_DELAY_MS: string; // Delay between retry attempts in milliseconds
    ERROR_NOTIFICATION_EMAIL: string; // Email address for error notifications
  }
}