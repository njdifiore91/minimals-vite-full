/**
 * Email Service Application
 * 
 * Core application setup module that configures the Email Service components and provides
 * the main application instance. Initializes logger, loads configuration, and creates service
 * instances for email monitoring, queue management, and storage.
 */

import { Server } from 'http';
import express, { Express, Request, Response } from 'express';
import { createTerminus } from '@godaddy/terminus';

// Import configuration
import { appConfig } from './config/app';
import { loggerConfig } from './config/logger';
import { imapConfig } from './config/imap';
import { rabbitmqConfig } from './config/rabbitmq';
import { s3Config } from './config/s3';

// Import services
import { EmailMonitorService } from './services/email-monitor.service';
import { MessageQueueService } from './services/message-queue.service';
import { StorageService } from './services/storage.service';
import { VirusScannerService } from './services/virus-scanner.service';
import { AttachmentProcessorService } from './services/attachment-processor.service';

// Import types
import { IAppConfig, IServiceConfig, ILogLevel } from './types/config';
import { IResult } from './types/common';

// Import utilities
import { createLogger } from './utils/logger';
import { createServiceError } from './utils/error';

/**
 * Main Application class for the Email Service
 * 
 * Manages the lifecycle of the service, including initialization, startup, and shutdown.
 * Acts as the central hub connecting all service components together.
 */
export class Application {
  private app: Express;
  private server: Server | null = null;
  private config: IServiceConfig;
  private logger: any; // Using any for logger type as it depends on the logging library
  private isShuttingDown = false;
  
  // Service instances
  private emailMonitorService: EmailMonitorService | null = null;
  private messageQueueService: MessageQueueService | null = null;
  private storageService: StorageService | null = null;
  private virusScannerService: VirusScannerService | null = null;
  private attachmentProcessorService: AttachmentProcessorService | null = null;

  /**
   * Creates a new Application instance
   * 
   * @param config Optional configuration override
   */
  constructor(config?: Partial<IServiceConfig>) {
    // Initialize Express application
    this.app = express();
    
    // Load configuration with optional overrides
    this.config = {
      app: { ...appConfig },
      logger: { ...loggerConfig },
      imap: { ...imapConfig },
      rabbitmq: { ...rabbitmqConfig },
      s3: { ...s3Config },
      ...config
    };
    
    // Initialize logger
    this.logger = createLogger(this.config.logger);
    this.logger.info('Email Service initializing', { 
      serviceName: this.config.app.serviceName,
      version: this.config.app.version,
      environment: this.config.app.environment
    });
    
    // Configure Express
    this.configureExpress();
  }

  /**
   * Configures the Express application with middleware and routes
   */
  private configureExpress(): void {
    // Add JSON body parser
    this.app.use(express.json());
    
    // Add basic request logging
    this.app.use((req: Request, res: Response, next) => {
      this.logger.info(`${req.method} ${req.path}`, { 
        requestId: req.headers['x-request-id'] || 'unknown',
        method: req.method,
        path: req.path
      });
      next();
    });
    
    // Configure health check endpoints for Kubernetes probes
    this.configureHealthChecks();
  }

  /**
   * Configures health check endpoints for Kubernetes probes
   */
  private configureHealthChecks(): void {
    // Liveness probe - simple endpoint to check if the service is running
    this.app.get('/health/live', (req: Request, res: Response) => {
      res.status(200).json({ status: 'ok' });
    });
    
    // Readiness probe - checks if the service is ready to accept requests
    this.app.get('/health/ready', async (req: Request, res: Response) => {
      // Check if all required services are initialized and connected
      const isReady = this.emailMonitorService !== null && 
                      this.messageQueueService !== null && 
                      this.storageService !== null;
      
      if (isReady) {
        res.status(200).json({ status: 'ready' });
      } else {
        res.status(503).json({ status: 'not ready' });
      }
    });
  }

  /**
   * Initializes all required services
   * 
   * @returns Promise that resolves when all services are initialized
   */
  private async initializeServices(): Promise<IResult<void>> {
    try {
      this.logger.info('Initializing services');
      
      // Initialize storage service
      this.storageService = new StorageService(this.config.s3, this.logger);
      await this.storageService.initialize();
      this.logger.info('Storage service initialized');
      
      // Initialize message queue service
      this.messageQueueService = new MessageQueueService(this.config.rabbitmq, this.logger);
      await this.messageQueueService.initialize();
      this.logger.info('Message queue service initialized');
      
      // Initialize virus scanner service
      this.virusScannerService = new VirusScannerService(this.logger);
      await this.virusScannerService.initialize();
      this.logger.info('Virus scanner service initialized');
      
      // Initialize attachment processor service
      this.attachmentProcessorService = new AttachmentProcessorService(
        this.storageService,
        this.virusScannerService,
        this.logger
      );
      await this.attachmentProcessorService.initialize();
      this.logger.info('Attachment processor service initialized');
      
      // Initialize email monitor service (depends on other services)
      this.emailMonitorService = new EmailMonitorService(
        this.config.imap,
        this.messageQueueService,
        this.attachmentProcessorService,
        this.logger
      );
      await this.emailMonitorService.initialize();
      this.logger.info('Email monitor service initialized');
      
      return { success: true };
    } catch (error) {
      const serviceError = createServiceError(
        'Failed to initialize services',
        error,
        'Application.initializeServices'
      );
      this.logger.error(serviceError.message, { error: serviceError });
      return { success: false, error: serviceError };
    }
  }

  /**
   * Starts the application and all its services
   * 
   * @returns Promise that resolves when the application is started
   */
  public async start(): Promise<IResult<void>> {
    try {
      this.logger.info('Starting Email Service');
      
      // Initialize services
      const initResult = await this.initializeServices();
      if (!initResult.success) {
        return initResult;
      }
      
      // Start email monitoring
      if (this.emailMonitorService) {
        await this.emailMonitorService.startMonitoring();
        this.logger.info('Email monitoring started');
      }
      
      // Start HTTP server
      return new Promise((resolve) => {
        this.server = this.app.listen(this.config.app.port, () => {
          this.logger.info(`Email Service listening on port ${this.config.app.port}`, {
            port: this.config.app.port,
            environment: this.config.app.environment
          });
          resolve({ success: true });
        });
        
        // Configure graceful shutdown with terminus
        this.configureGracefulShutdown();
      });
    } catch (error) {
      const serviceError = createServiceError(
        'Failed to start application',
        error,
        'Application.start'
      );
      this.logger.error(serviceError.message, { error: serviceError });
      return { success: false, error: serviceError };
    }
  }

  /**
   * Configures graceful shutdown handling with terminus
   */
  private configureGracefulShutdown(): void {
    if (!this.server) {
      return;
    }
    
    createTerminus(this.server, {
      signal: 'SIGINT',
      healthChecks: {
        '/health/live': async () => {
          return { status: 'ok' };
        },
        '/health/ready': async () => {
          if (this.isShuttingDown) {
            throw new Error('Server is shutting down');
          }
          return { status: 'ready' };
        },
      },
      onSignal: async () => {
        this.logger.info('Shutdown signal received');
        this.isShuttingDown = true;
        await this.stop();
      },
      onShutdown: async () => {
        this.logger.info('Cleanup completed, server is shutting down');
      },
      logger: (msg, err) => {
        if (err) {
          this.logger.error(msg, { error: err });
        } else {
          this.logger.info(msg);
        }
      },
    });
  }

  /**
   * Stops the application and all its services
   * 
   * @returns Promise that resolves when the application is stopped
   */
  public async stop(): Promise<IResult<void>> {
    try {
      this.logger.info('Stopping Email Service');
      
      // Stop email monitoring
      if (this.emailMonitorService) {
        await this.emailMonitorService.stopMonitoring();
        this.logger.info('Email monitoring stopped');
      }
      
      // Close message queue connection
      if (this.messageQueueService) {
        await this.messageQueueService.close();
        this.logger.info('Message queue connection closed');
      }
      
      // Close storage service
      if (this.storageService) {
        await this.storageService.close();
        this.logger.info('Storage service closed');
      }
      
      // Close HTTP server if it's running
      if (this.server) {
        return new Promise((resolve) => {
          this.server!.close(() => {
            this.logger.info('HTTP server closed');
            this.server = null;
            resolve({ success: true });
          });
        });
      }
      
      return { success: true };
    } catch (error) {
      const serviceError = createServiceError(
        'Failed to stop application',
        error,
        'Application.stop'
      );
      this.logger.error(serviceError.message, { error: serviceError });
      return { success: false, error: serviceError };
    }
  }

  /**
   * Returns the Express application instance
   * 
   * @returns Express application instance
   */
  public getApp(): Express {
    return this.app;
  }

  /**
   * Returns the HTTP server instance
   * 
   * @returns HTTP server instance or null if not started
   */
  public getServer(): Server | null {
    return this.server;
  }

  /**
   * Returns the application configuration
   * 
   * @returns Application configuration
   */
  public getConfig(): IServiceConfig {
    return this.config;
  }
}

// Export a default instance for convenience
export default new Application();