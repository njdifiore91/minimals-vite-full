/**
 * Notification Service - Main Entry Point
 * 
 * This is the main entry point for the Notification Service microservice.
 * It initializes the application, sets up error handling, connects to RabbitMQ,
 * and starts the notification processing.
 */

import { createServer } from 'http';
import amqplib from 'amqplib';

// Import configuration
import { appConfig, rabbitmqConfig, loggerConfig } from './config';

// Import services
import { 
  NotificationService, 
  WebhookService, 
  RetryService, 
  AuditService 
} from './services';

// Import types
import { IRabbitMQConnection } from './types';

// Setup logger
import pino from 'pino';
const logger = pino(loggerConfig);

// Global error handlers
process.on('uncaughtException', (error) => {
  logger.error({ err: error }, 'Uncaught exception');
  // Give logger time to flush before exiting
  setTimeout(() => process.exit(1), 500);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error({ reason, promise }, 'Unhandled rejection');
});

// Create HTTP server for health checks
const server = createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok' }));
  } else {
    res.writeHead(404);
    res.end();
  }
});

// Track connections for graceful shutdown
let rabbitMQConnection: amqplib.Connection | null = null;
let rabbitMQChannel: amqplib.Channel | null = null;
let notificationService: NotificationService | null = null;

/**
 * Initialize RabbitMQ connection with TLS
 */
async function initializeRabbitMQ(): Promise<{ connection: amqplib.Connection, channel: amqplib.Channel }> {
  try {
    logger.info('Connecting to RabbitMQ...');
    
    // Create connection options with TLS settings
    const connectionOptions: IRabbitMQConnection = {
      protocol: rabbitmqConfig.protocol,
      hostname: rabbitmqConfig.hostname,
      port: rabbitmqConfig.port,
      username: rabbitmqConfig.username,
      password: rabbitmqConfig.password,
      vhost: rabbitmqConfig.vhost,
      tls: {
        enabled: rabbitmqConfig.tls.enabled,
        ca: rabbitmqConfig.tls.ca ? [rabbitmqConfig.tls.ca] : undefined,
        cert: rabbitmqConfig.tls.cert,
        key: rabbitmqConfig.tls.key,
        rejectUnauthorized: rabbitmqConfig.tls.rejectUnauthorized
      }
    };
    
    // Connect to RabbitMQ
    const connection = await amqplib.connect(connectionOptions);
    
    // Handle connection errors
    connection.on('error', (err) => {
      logger.error({ err }, 'RabbitMQ connection error');
      setTimeout(() => {
        logger.info('Attempting to reconnect to RabbitMQ...');
        initializeRabbitMQ().catch(err => {
          logger.error({ err }, 'Failed to reconnect to RabbitMQ');
        });
      }, 5000);
    });
    
    // Create channel
    const channel = await connection.createChannel();
    
    // Ensure queue exists
    await channel.assertQueue(rabbitmqConfig.queue, {
      durable: true,
      arguments: rabbitmqConfig.queueArguments
    });
    
    logger.info('Successfully connected to RabbitMQ');
    
    return { connection, channel };
  } catch (error) {
    logger.error({ err: error }, 'Failed to connect to RabbitMQ');
    throw error;
  }
}

/**
 * Initialize services
 */
async function initializeServices(channel: amqplib.Channel): Promise<NotificationService> {
  // Initialize supporting services
  const auditService = new AuditService();
  const retryService = new RetryService();
  const webhookService = new WebhookService(retryService, auditService);
  
  // Initialize main notification service
  const notificationService = new NotificationService(channel, webhookService, auditService);
  
  return notificationService;
}

/**
 * Start the application
 */
async function start() {
  try {
    logger.info(`Starting ${appConfig.serviceName} v${appConfig.version}...`);
    
    // Initialize RabbitMQ
    const { connection, channel } = await initializeRabbitMQ();
    rabbitMQConnection = connection;
    rabbitMQChannel = channel;
    
    // Initialize services
    notificationService = await initializeServices(channel);
    
    // Start processing notifications
    await notificationService.start();
    
    // Start HTTP server for health checks
    server.listen(appConfig.port, () => {
      logger.info(`Health check server listening on port ${appConfig.port}`);
    });
    
    logger.info(`${appConfig.serviceName} started successfully`);
  } catch (error) {
    logger.error({ err: error }, 'Failed to start application');
    process.exit(1);
  }
}

/**
 * Graceful shutdown
 */
async function shutdown() {
  logger.info('Shutting down gracefully...');
  
  // Stop notification processing
  if (notificationService) {
    try {
      await notificationService.stop();
      logger.info('Notification service stopped');
    } catch (error) {
      logger.error({ err: error }, 'Error stopping notification service');
    }
  }
  
  // Close RabbitMQ channel
  if (rabbitMQChannel) {
    try {
      await rabbitMQChannel.close();
      logger.info('RabbitMQ channel closed');
    } catch (error) {
      logger.error({ err: error }, 'Error closing RabbitMQ channel');
    }
  }
  
  // Close RabbitMQ connection
  if (rabbitMQConnection) {
    try {
      await rabbitMQConnection.close();
      logger.info('RabbitMQ connection closed');
    } catch (error) {
      logger.error({ err: error }, 'Error closing RabbitMQ connection');
    }
  }
  
  // Close HTTP server
  server.close(() => {
    logger.info('HTTP server closed');
    
    // Give logger time to flush before exiting
    setTimeout(() => {
      logger.info('Shutdown complete');
      process.exit(0);
    }, 500);
  });
  
  // Force exit after timeout if graceful shutdown fails
  setTimeout(() => {
    logger.error('Forced shutdown after timeout');
    process.exit(1);
  }, 10000);
}

// Handle termination signals
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);

// Start the application
start().catch((error) => {
  logger.error({ err: error }, 'Fatal error during startup');
  process.exit(1);
});