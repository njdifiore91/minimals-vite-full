/**
 * Notification Service - Main Entry Point
 *
 * This is the main entry point for the Notification Service microservice. It initializes the application,
 * sets up error handling, connects to RabbitMQ, and starts the notification processing. It also handles
 * graceful shutdown when the process is terminated.
 *
 * The Notification Service is responsible for handling alerts and webhooks, consuming messages from RabbitMQ,
 * and delivering notifications to configured endpoints with retry capability.
 */

import { Connection, Channel, connect } from 'amqplib';
import { v4 as uuidv4 } from 'uuid';

// Import configuration and utilities
import { config } from './config';
import { logger } from './config/logger';
import { getRabbitMQConnectionOptions, getQueueOptions, getConsumerOptions } from './config/rabbitmq';
import { ILogContext } from './types';

// Import services
import { WebhookService } from './services/webhook-service';
import { MessageService } from './services/message-service';
import { RetryService } from './services/retry-service';
import { AuditService } from './services/audit-service';
import { NotificationService } from './services/notification-service';

// Create a unique service instance ID for logging and tracking
const serviceInstanceId = uuidv4();

// Create a base logging context
const baseLogContext: ILogContext = {
  serviceId: serviceInstanceId,
  serviceName: config.app.name,
  serviceVersion: config.app.version,
  environment: config.app.environment
};

// Initialize logger with base context
const serviceLogger = logger.child(baseLogContext);

// Track connections for graceful shutdown
let rabbitMQConnection: Connection | null = null;
let rabbitMQChannel: Channel | null = null;
let notificationService: NotificationService | null = null;

/**
 * Initialize RabbitMQ connection and channel
 * @returns Promise that resolves to a RabbitMQ channel
 */
async function initializeRabbitMQ(): Promise<Channel> {
  serviceLogger.info('Initializing RabbitMQ connection', { 
    host: config.rabbitmq.host,
    port: config.rabbitmq.port,
    vhost: config.rabbitmq.vhost,
    tls: config.rabbitmq.tls
  });

  try {
    // Connect to RabbitMQ with TLS if enabled
    const connectionOptions = getRabbitMQConnectionOptions();
    rabbitMQConnection = await connect(connectionOptions);
    
    // Log successful connection
    serviceLogger.info('Successfully connected to RabbitMQ');
    
    // Handle connection errors and closed events
    rabbitMQConnection.on('error', (err) => {
      serviceLogger.error('RabbitMQ connection error', { error: err.message });
      // Don't attempt reconnection here - let the process exit and be restarted by the container orchestrator
    });
    
    rabbitMQConnection.on('close', () => {
      serviceLogger.warn('RabbitMQ connection closed');
      // Don't attempt reconnection here - let the process exit and be restarted by the container orchestrator
    });
    
    // Create a channel
    rabbitMQChannel = await rabbitMQConnection.createChannel();
    
    // Set prefetch count to control concurrency
    await rabbitMQChannel.prefetch(config.rabbitmq.prefetchCount);
    
    // Log successful channel creation
    serviceLogger.info('Successfully created RabbitMQ channel', { 
      prefetchCount: config.rabbitmq.prefetchCount 
    });
    
    // Handle channel errors and closed events
    rabbitMQChannel.on('error', (err) => {
      serviceLogger.error('RabbitMQ channel error', { error: err.message });
    });
    
    rabbitMQChannel.on('close', () => {
      serviceLogger.warn('RabbitMQ channel closed');
    });
    
    // Assert the exchange
    await rabbitMQChannel.assertExchange(
      config.rabbitmq.exchange,
      config.rabbitmq.exchangeType,
      { durable: config.rabbitmq.exchangeDurable }
    );
    
    // Assert the notification queue
    await rabbitMQChannel.assertQueue(
      config.rabbitmq.queue,
      getQueueOptions()
    );
    
    // Bind the queue to the exchange
    await rabbitMQChannel.bindQueue(
      config.rabbitmq.queue,
      config.rabbitmq.exchange,
      config.rabbitmq.routingKey || ''
    );
    
    // Assert the dead letter exchange and queue
    await rabbitMQChannel.assertExchange(
      config.rabbitmq.deadLetterExchange,
      'direct',
      { durable: true }
    );
    
    await rabbitMQChannel.assertQueue(
      config.rabbitmq.deadLetterRoutingKey,
      { 
        durable: true,
        arguments: {
          'x-message-ttl': config.rabbitmq.messageTTL
        }
      }
    );
    
    await rabbitMQChannel.bindQueue(
      config.rabbitmq.deadLetterRoutingKey,
      config.rabbitmq.deadLetterExchange,
      config.rabbitmq.deadLetterRoutingKey
    );
    
    serviceLogger.info('Successfully set up RabbitMQ exchanges and queues');
    
    return rabbitMQChannel;
  } catch (error) {
    serviceLogger.error('Failed to initialize RabbitMQ', { error });
    throw error;
  }
}

/**
 * Initialize all services required by the Notification Service
 * @param channel RabbitMQ channel
 * @returns Object containing initialized services
 */
function initializeServices(channel: Channel) {
  serviceLogger.info('Initializing services');
  
  // Initialize the webhook service
  const webhookService = new WebhookService(baseLogContext);
  
  // Initialize the message service for email, SMS, and push notifications
  const messageService = new MessageService(baseLogContext);
  
  // Initialize the retry service for failed deliveries
  const retryService = new RetryService(channel, baseLogContext);
  
  // Initialize the audit service for logging
  const auditService = new AuditService(baseLogContext);
  
  // Initialize the notification service
  const notificationService = new NotificationService(
    channel,
    webhookService,
    messageService,
    retryService,
    auditService,
    baseLogContext
  );
  
  serviceLogger.info('Services initialized successfully');
  
  return {
    webhookService,
    messageService,
    retryService,
    auditService,
    notificationService
  };
}

/**
 * Start the Notification Service
 */
async function startService() {
  serviceLogger.info('Starting Notification Service', {
    version: config.app.version,
    environment: config.app.environment,
    nodeEnv: process.env.NODE_ENV
  });
  
  try {
    // Initialize RabbitMQ
    const channel = await initializeRabbitMQ();
    
    // Initialize services
    const services = initializeServices(channel);
    notificationService = services.notificationService;
    
    // Start consuming messages
    await notificationService.startConsuming();
    
    serviceLogger.info('Notification Service started successfully');
  } catch (error) {
    serviceLogger.error('Failed to start Notification Service', { error });
    // Exit with error code to signal failure to the container orchestrator
    process.exit(1);
  }
}

/**
 * Gracefully shut down the Notification Service
 * @param signal The signal that triggered the shutdown
 */
async function shutdownService(signal: string) {
  serviceLogger.info(`Received ${signal}, shutting down gracefully...`);
  
  try {
    // Stop consuming messages
    if (notificationService) {
      serviceLogger.info('Stopping notification service...');
      await notificationService.stopConsuming();
    }
    
    // Close RabbitMQ channel
    if (rabbitMQChannel) {
      serviceLogger.info('Closing RabbitMQ channel...');
      await rabbitMQChannel.close();
      rabbitMQChannel = null;
    }
    
    // Close RabbitMQ connection
    if (rabbitMQConnection) {
      serviceLogger.info('Closing RabbitMQ connection...');
      await rabbitMQConnection.close();
      rabbitMQConnection = null;
    }
    
    serviceLogger.info('Graceful shutdown completed');
    process.exit(0);
  } catch (error) {
    serviceLogger.error('Error during graceful shutdown', { error });
    process.exit(1);
  }
}

/**
 * Set up global error handlers
 */
function setupErrorHandlers() {
  // Handle uncaught exceptions
  process.on('uncaughtException', (error) => {
    serviceLogger.error('Uncaught exception', { error });
    // Exit with error code to signal failure to the container orchestrator
    process.exit(1);
  });
  
  // Handle unhandled promise rejections
  process.on('unhandledRejection', (reason, promise) => {
    serviceLogger.error('Unhandled promise rejection', { reason, promise });
    // Exit with error code to signal failure to the container orchestrator
    process.exit(1);
  });
  
  // Handle termination signals
  process.on('SIGTERM', () => shutdownService('SIGTERM'));
  process.on('SIGINT', () => shutdownService('SIGINT'));
}

// Set up error handlers
setupErrorHandlers();

// Start the service
startService().catch((error) => {
  serviceLogger.error('Fatal error starting service', { error });
  process.exit(1);
});