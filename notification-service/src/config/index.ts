/**
 * Configuration Module for Notification Service
 *
 * This file serves as the central entry point (barrel file) for the Notification Service configuration module.
 * It aggregates and re-exports all configuration components to present a single, cohesive API surface.
 * This file simplifies importing configuration throughout the service and ensures consistent configuration usage.
 *
 * @module config
 */

// Export application configuration
// This should be first as other modules may depend on it
export * from './app';

// Export logger configuration
export * from './logger';

// Export Redis configuration
export * from './redis';

// Export RabbitMQ configuration
export * from './rabbitmq';

// Export webhook configuration
export * from './webhook';

// Export default configuration object
import config from './app';
export default config;