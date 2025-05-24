/**
 * Email Service Configuration Module
 * 
 * This barrel file aggregates and re-exports all configuration components
 * to present a single, cohesive API surface. It simplifies importing
 * configuration throughout the service and ensures consistent configuration usage.
 */

// Core application configuration
export * from './app';

// IMAP connection settings
export * from './imap';

// Logging system configuration
export * from './logger';

// RabbitMQ connection and messaging settings
export * from './rabbitmq';

// S3-compatible storage client configuration
export * from './s3';