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
import { appConfig, imapConfig, rabbitMQConfig, s3Config } from './config';
import { logger } from './config/logger';

// Import services
import {
  EmailMonitorService,
  MessageQueueService,
  StorageService,
  VirusScannerService,
} from './services';

// Import utility functions
import { formatTime } from './utils';
import { createServiceError } from './utils/error';

// Initialize services
let emailMonitorService: EmailMonitorService | null = null;
let messageQueueService: MessageQueueService | null = null;
let storageService: StorageService | null = null;
let virusScannerService: VirusScannerService | null = null;

// Create a simple health check server
const server = createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', timestamp: formatTime(new Date()) }));
  } else {
    res.writeHead(404);
    res.end();
  }
});

/**
 * Handle uncaught exceptions
 */
process.on('uncaughtException', (error) => {
  logger.error(
    createServiceError('Uncaught exception', {
      error,
      context: 'process.uncaughtException',
    })
  );
  // Perform graceful shutdown
  shutdown(1);
});

/**
 * Handle unhandled promise rejections
 */
process.on('unhandledRejection', (reason, promise) => {
  logger.error(
    createServiceError('Unhandled promise rejection', {
      error: reason,
      context: 'process.unhandledRejection',
    })
  );
});

/**
 * Handle termination signals for graceful shutdown
 */
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down gracefully');
  shutdown(0);
});

process.on('SIGINT', () => {
  logger.info('SIGINT received, shutting down gracefully');
  shutdown(0);
});

/**
 * Graceful shutdown function
 * Closes all connections and exits the process
 */
async function shutdown(exitCode: number): Promise<void> {
  logger.info('Shutting down Email Service...');
  
  // Set a timeout for shutdown to ensure the process exits
  const shutdownTimeout = setTimeout(() => {
    logger.error('Shutdown timed out, forcing exit');
    process.exit(exitCode);
  }, 10000); // 10 seconds timeout
  
  try {
    // Stop the health check server
    server.close();
    
    // Stop the email monitor service
    if (emailMonitorService) {
      logger.info('Stopping email monitor service...');
      await emailMonitorService.stop();
      emailMonitorService = null;
    }
    
    // Close the message queue connection
    if (messageQueueService) {
      logger.info('Closing message queue connection...');
      await messageQueueService.close();
      messageQueueService = null;
    }
    
    // Close the storage service
    if (storageService) {
      logger.info('Closing storage service...');
      await storageService.close();
      storageService = null;
    }
    
    // Close the virus scanner service
    if (virusScannerService) {
      logger.info('Closing virus scanner service...');
      await virusScannerService.close();
      virusScannerService = null;
    }
    
    logger.info('All connections closed, exiting process');
    clearTimeout(shutdownTimeout);
    process.exit(exitCode);
  } catch (error) {
    logger.error(
      createServiceError('Error during shutdown', {
        error,
        context: 'shutdown',
      })
    );
    clearTimeout(shutdownTimeout);
    process.exit(1); // Exit with error code
  }
}

/**
 * Initialize and start the Email Service
 */
async function startService(): Promise<void> {
  try {
    logger.info(`Starting ${appConfig.serviceName} v${appConfig.version}...`);
    
    // Initialize the virus scanner service
    logger.info('Initializing virus scanner service...');
    virusScannerService = new VirusScannerService();
    await virusScannerService.initialize();
    
    // Initialize the storage service
    logger.info('Initializing storage service...');
    storageService = new StorageService(s3Config);
    await storageService.initialize();
    
    // Initialize the message queue service
    logger.info('Connecting to RabbitMQ...');
    messageQueueService = new MessageQueueService(rabbitMQConfig);
    await messageQueueService.connect();
    
    // Initialize and start the email monitor service
    logger.info('Starting email monitoring service...');
    emailMonitorService = new EmailMonitorService(
      imapConfig,
      messageQueueService,
      storageService,
      virusScannerService
    );
    await emailMonitorService.start();
    
    // Start the health check server
    server.listen(appConfig.port, () => {
      logger.info(`Health check server listening on port ${appConfig.port}`);
    });
    
    logger.info(`${appConfig.serviceName} started successfully`);
    logger.info(`Environment: ${appConfig.environment}`);
    logger.info(`Monitoring inbox: ${imapConfig.user}`);
    logger.info(`Polling interval: ${imapConfig.pollingInterval}ms`);
  } catch (error) {
    logger.error(
      createServiceError('Failed to start Email Service', {
        error,
        context: 'startService',
      })
    );
    // Shutdown with error code
    await shutdown(1);
  }
}

// Start the service
startService().catch((error) => {
  logger.error(
    createServiceError('Unhandled error during service startup', {
      error,
      context: 'startService',
    })
  );
  process.exit(1);
});