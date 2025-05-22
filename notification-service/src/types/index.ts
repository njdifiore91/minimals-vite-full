/**
 * @file index.ts
 * @description Barrel file that exports all type definitions from the Notification Service types module.
 * This file simplifies importing types throughout the service by providing a single entry point.
 * It ensures consistent type usage and enables tree-shaking for optimized builds.
 */

// Export common types first as they may be dependencies for other type modules
export * from './common';

// Export configuration types
export * from './config';

// Export message queue related types
export * from './rabbitmq';

// Export domain-specific types
export * from './message';
export * from './notification';
export * from './webhook';