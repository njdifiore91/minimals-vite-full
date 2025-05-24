/**
 * Type Definitions Index
 * 
 * This barrel file exports all type definitions from the Notification Service types module.
 * It simplifies importing types throughout the service by providing a single entry point,
 * ensures consistent type usage, and enables tree-shaking for optimized builds.
 */

// Export common types (base types used by other modules)
export * from './common';

// Export configuration types
export * from './config';

// Export message types
export * from './message';

// Export webhook types
export * from './webhook';

// Export notification types
export * from './notification';

// Export RabbitMQ types
export * from './rabbitmq';