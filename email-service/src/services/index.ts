/**
 * Email Service - Services Barrel File
 * 
 * This file serves as the central export point for all service implementations
 * in the Email Service. It provides a unified API surface for importing services
 * throughout the application while enabling tree-shaking for optimized builds.
 */

// Core email monitoring functionality
export * from './email-monitor.service';

// Attachment processing functionality
export * from './attachment-processor.service';

// Virus scanning functionality
export * from './virus-scanner.service';

// Storage functionality for email attachments
export * from './storage.service';

// Message queue functionality for service communication
export * from './message-queue.service';