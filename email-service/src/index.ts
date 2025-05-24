/**
 * Email Service - Main Entry Point
 * 
 * This is the main entry point for the Email Service microservice. It initializes the application,
 * sets up error handling, connects to required services (IMAP, RabbitMQ, S3), and starts the
 * email monitoring process. It also handles graceful shutdown when the process is terminated.
 */

import { createServer } from 'http';
import process from 'process';

// Import configuration
import { config } from './config/app';
import { logger, setupLogger } from './config/logger';
import { setupRabbitMQ } from './config/rabbitmq';
import { setupS3Client } from './config/s3';

// Import services
import { 
  EmailMonitorService,
  MessageQueueService,
  StorageService,
  VirusScannerService,
  AttachmentProcessorService
} from './services';

// Import utilities
import { handleError } from './utils/error';

/**
 * Initialize the application
 */
async function bootstrap() {
  try {
    // Set up logger first to capture initialization logs
    setupLogger();
    logger.info(`Starting ${config.serviceName} v${config.version}`);
    logger.info(`Environment: ${config.nodeEnv}`);

    // Initialize services
    logger.info('Initializing services...');
    
    // Set up S3 client for document storage
    logger.info('Connecting to S3 storage...');
    const s3Client = await setupS3Client();
    const storageService = new StorageService(s3Client, config.s3);
    logger.info('S3 storage connection established');
    
    // Set up RabbitMQ connection
    logger.info('Connecting to RabbitMQ...');
    const rabbitMQConnection = await setupRabbitMQ();
    const messageQueueService = new MessageQueueService(rabbitMQConnection, config.rabbitmq);
    logger.info('RabbitMQ connection established');
    
    // Initialize virus scanner service
    logger.info('Initializing virus scanner...');
    const virusScannerService = new VirusScannerService(config.virusScanner);
    logger.info('Virus scanner initialized');
    
    // Initialize attachment processor service
    logger.info('Initializing attachment processor...');
    const attachmentProcessorService = new AttachmentProcessorService(
      virusScannerService,
      storageService,
      messageQueueService
    );
    logger.info('Attachment processor initialized');
    
    // Initialize email monitor service
    logger.info('Initializing email monitor...');
    const emailMonitorService = new EmailMonitorService(
      config.imap,
      attachmentProcessorService
    );
    logger.info('Email monitor initialized');
    
    // Create a simple HTTP server for health checks
    const server = createServer((req, res) => {
      if (req.url === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'ok', service: config.serviceName, version: config.version }));
      } else {
        res.writeHead(404);
        res.end();
      }
    });
    
    server.listen(config.port, () => {
      logger.info(`Health check server listening on port ${config.port}`);
    });
    
    // Start email monitoring
    logger.info('Starting email monitoring...');
    await emailMonitorService.startMonitoring();
    logger.info('Email monitoring started');
    
    // Set up graceful shutdown
    setupGracefulShutdown({
      server,
      emailMonitorService,
      messageQueueService,
      storageService
    });
    
    logger.info(`${config.serviceName} is running`);
  } catch (error) {
    logger.error('Failed to start the application', { error: handleError(error) });
    process.exit(1);
  }
}

/**
 * Set up graceful shutdown to close connections when the process terminates
 */
function setupGracefulShutdown({
  server,
  emailMonitorService,
  messageQueueService,
  storageService
}: {
  server: ReturnType<typeof createServer>;
  emailMonitorService: EmailMonitorService;
  messageQueueService: MessageQueueService;
  storageService: StorageService;
}) {
  // Handle process termination signals
  const shutdownHandler = async (signal: string) => {
    logger.info(`Received ${signal}. Shutting down gracefully...`);
    
    try {
      // Stop the HTTP server first to prevent new health check requests
      await new Promise<void>((resolve) => {
        server.close(() => resolve());
      });
      logger.info('Health check server stopped');
      
      // Stop email monitoring
      await emailMonitorService.stopMonitoring();
      logger.info('Email monitoring stopped');
      
      // Close message queue connection
      await messageQueueService.close();
      logger.info('RabbitMQ connection closed');
      
      // Close storage connection
      await storageService.close();
      logger.info('S3 storage connection closed');
      
      logger.info('Graceful shutdown completed');
      process.exit(0);
    } catch (error) {
      logger.error('Error during graceful shutdown', { error: handleError(error) });
      process.exit(1);
    }
  };
  
  // Register shutdown handlers for different signals
  process.on('SIGTERM', () => shutdownHandler('SIGTERM'));
  process.on('SIGINT', () => shutdownHandler('SIGINT'));
  
  // Handle uncaught exceptions and unhandled rejections
  process.on('uncaughtException', (error) => {
    logger.error('Uncaught exception', { error: handleError(error) });
    // Attempt graceful shutdown
    shutdownHandler('uncaughtException');
  });
  
  process.on('unhandledRejection', (reason) => {
    logger.error('Unhandled rejection', { reason: handleError(reason) });
    // Attempt graceful shutdown
    shutdownHandler('unhandledRejection');
  });
}

// Start the application
bootstrap();