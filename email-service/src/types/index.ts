/**
 * Email Service Type Definitions
 * 
 * This barrel file exports all type definitions used throughout the Email Service.
 * It provides a single entry point for importing types, simplifying imports and
 * preventing circular dependencies.
 * 
 * The Email Service is implemented in TypeScript for type safety as specified in
 * section 3.1.1 of the technical specification. This modular approach to type
 * definitions supports maintainability and enables tree-shaking for optimized builds.
 */

// Common types used throughout the application
// These are exported first to prevent circular dependencies
export * from './common';

// Configuration types for the Email Service
export * from './config';

// Storage types for S3-compatible document storage
export * from './storage';

// Message queue types for RabbitMQ integration
export * from './message-queue';

// Email processing types
export * from './email';