/**
 * Email Service Type Definitions
 * 
 * This barrel file exports all type definitions used throughout the Email Service.
 * It provides a single entry point for importing types, simplifying imports and
 * preventing circular dependencies.
 * 
 * @module types
 */

// Common types used throughout the application
export * from './common';

// Configuration types for service settings and environment variables
export * from './config';

// Email message types for processing incoming emails
export * from './email';

// Error handling and logging types
export * from './error';

// IMAP connection and mailbox operation types
export * from './imap';

// Message queue types for RabbitMQ integration
export * from './message-queue';

// Storage types for S3-compatible document storage
export * from './storage';