/**
 * Email Service - Services Barrel File
 * 
 * This file serves as the central entry point for all service implementations
 * in the Email Service. It re-exports all service modules to provide a unified
 * API surface, simplifying imports throughout the application and enabling
 * tree-shaking for optimized builds.
 */

// Core email monitoring service
export * from './email-monitor.service';

// Email attachment processing
export * from './attachment-processor.service';

// Security scanning
export * from './virus-scanner.service';

// Storage and messaging services
export * from './storage.service';
export * from './message-queue.service';