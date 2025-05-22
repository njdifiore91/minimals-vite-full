/**
 * Configuration module for the Notification Service
 * 
 * This barrel file exports all configuration components to present a single, cohesive API surface.
 * It simplifies importing configuration throughout the service and ensures consistent configuration usage.
 */

// Export all configuration modules
export { default as appConfig } from './app';
export { default as loggerConfig } from './logger';
export { default as redisConfig } from './redis';
export { default as webhookConfig } from './webhook';
export { default as rabbitMQConfig } from './rabbitmq';

// Export helper functions
export {
  getConnectionUrl as getRabbitMQConnectionUrl,
  validateRabbitMQConfig,
  loadTlsCertificates,
  getRabbitMQConnectionOptions,
  getQueueOptions,
  getConsumerOptions,
  getPublishOptions
} from './rabbitmq';