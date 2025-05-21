/**
 * @module types
 * @description Central barrel file for Email Service type definitions
 * 
 * This file re-exports all type modules to provide a unified API surface.
 * It simplifies importing types throughout the application by allowing
 * consumers to import from a single path rather than individual type files.
 * 
 * Example usage:
 * ```typescript
 * import { IEmailMessage, IServiceError, IAppConfig } from '../types';
 * ```
 * 
 * Note: When adding new type modules, ensure they are exported here to maintain
 * a consistent import pattern across the application.
 */

// Common types
export * from './common';

// Error handling types
export * from './error';

// Configuration types
export * from './config';

// Email and message types
export * from './email';
export * from './imap';

// Storage types
export * from './storage';

// Message queue types
export * from './message-queue';