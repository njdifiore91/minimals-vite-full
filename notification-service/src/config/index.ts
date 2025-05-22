/**
 * Configuration module for the Notification Service
 * 
 * This barrel file exports all configuration components to present a single, cohesive API surface.
 * It simplifies importing configuration throughout the service and ensures consistent configuration usage.
 */

// Export all configuration modules
export { default as config } from './app';
export { default as logger } from './logger';
export { default as redis } from './redis';
export { default as webhook } from './webhook';
export { default as rabbitmq } from './rabbitmq';

// Export helper functions from app.ts
export {
  getEnv,
  getNumericEnv,
  getBooleanEnv,
  getArrayEnv,
  getEnvironment,
  getLogLevel,
  validateConfig
} from './app';

// Export helper functions from rabbitmq.ts
export {
  getConnectionUrl as getRabbitMQConnectionUrl,
  validateRabbitMQConfig,
  loadTlsCertificates,
  getRabbitMQConnectionOptions,
  getQueueOptions,
  getConsumerOptions,
  getPublishOptions
} from './rabbitmq';