/**
 * Email Service Application
 * 
 * Core application setup module that configures the Email Service components and provides
 * the main application instance. Initializes logger, loads configuration, and creates
 * service instances for email monitoring, queue management, and storage.
 *
 * This is the central hub that connects all service components together and manages
 * the application lifecycle including startup, shutdown, and health monitoring.
 */

import express, { Express, Request, Response } from 'express';
import http from 'http';
import { createLogger } from './utils/logger';
import { appConfig } from './config/app';
import { EmailMonitorService } from './services/email-monitor.service';
import { MessageQueueService } from './services/message-queue.service';
import { StorageService } from './services/storage.service';
import { VirusScannerService } from './services/virus-scanner.service';
import { AttachmentProcessorService } from './services/attachment-processor.service';

/**
 * Application class that manages the Email Service lifecycle
 */
export class Application {
  private app: Express;
  private server: http.Server | null = null;
  private logger = createLogger('Application');
  private emailMonitorService: EmailMonitorService;
  private messageQueueService: MessageQueueService;
  private storageService: StorageService;
  private virusScannerService: VirusScannerService;
  private attachmentProcessorService: AttachmentProcessorService;
  private isShuttingDown = false;

  /**
   * Creates a new Application instance
   * Initializes all required services and configures the Express application
   */
  constructor() {
    // Create Express application
    this.app = express();
    this.logger.info(`Initializing ${appConfig.serviceName} v${appConfig.version}`);
    this.logger.info(`Environment: ${appConfig.environment}`);
    
    try {
      // Initialize services in dependency order
      this.logger.info('Initializing services...');
      
      // Storage service for S3-compatible document storage
      this.storageService = new StorageService();
      this.logger.info('Storage service initialized');
      
      // Message queue service for RabbitMQ integration
      this.messageQueueService = new MessageQueueService();
      this.logger.info('Message queue service initialized');
      
      // Virus scanner service for attachment security
      this.virusScannerService = new VirusScannerService();
      this.logger.info('Virus scanner service initialized');
      
      // Attachment processor for handling email attachments
      this.attachmentProcessorService = new AttachmentProcessorService(
        this.virusScannerService,
        this.storageService
      );
      this.logger.info('Attachment processor service initialized');
      
      // Email monitor service for IMAP inbox monitoring
      this.emailMonitorService = new EmailMonitorService(
        this.attachmentProcessorService,
        this.messageQueueService
      );
      this.logger.info('Email monitor service initialized');

      // Configure Express middleware and routes
      this.configureMiddleware();
      this.configureRoutes();
      this.logger.info('Express application configured');
    } catch (error) {
      this.logger.error('Failed to initialize application', error);
      throw new Error(`Application initialization failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Configures Express middleware for request parsing, logging, and security
   */
  private configureMiddleware(): void {
    // Parse JSON request bodies
    this.app.use(express.json({ limit: '1mb' }));
    
    // Parse URL-encoded request bodies
    this.app.use(express.urlencoded({ extended: true, limit: '1mb' }));
    
    // Add security headers
    this.app.use((req: Request, res: Response, next) => {
      // Set security headers
      res.setHeader('X-Content-Type-Options', 'nosniff');
      res.setHeader('X-Frame-Options', 'DENY');
      res.setHeader('X-XSS-Protection', '1; mode=block');
      res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
      next();
    });
    
    // Add request logging middleware with correlation ID
    this.app.use((req: Request, res: Response, next) => {
      // Generate or extract correlation ID for request tracking
      const correlationId = req.headers['x-correlation-id'] as string || 
                           `${appConfig.serviceName}-${Date.now()}-${Math.random().toString(36).substring(2, 10)}`;
      
      // Add correlation ID to response headers
      res.setHeader('x-correlation-id', correlationId);
      
      // Log the incoming request with correlation ID
      this.logger.info(`${req.method} ${req.path}`, { correlationId, ip: req.ip });
      
      // Track response time
      const startTime = Date.now();
      res.on('finish', () => {
        const duration = Date.now() - startTime;
        this.logger.info(`${req.method} ${req.path} ${res.statusCode} ${duration}ms`, { 
          correlationId, 
          statusCode: res.statusCode,
          duration
        });
      });
      
      next();
    });
  }

  /**
   * Configures Express routes including health checks for Kubernetes probes
   * as required by section 3.2.3 of the technical specification
   */
  private configureRoutes(): void {
    // Health check endpoint for Kubernetes liveness probe
    this.app.get('/health/liveness', (req: Request, res: Response) => {
      res.status(200).json({ 
        status: 'UP',
        timestamp: new Date().toISOString(),
        service: appConfig.serviceName,
        version: appConfig.version
      });
    });

    // Health check endpoint for Kubernetes readiness probe
    this.app.get('/health/readiness', async (req: Request, res: Response) => {
      try {
        // Check if all required services are ready
        const storageReady = await this.storageService.isReady();
        const queueReady = await this.messageQueueService.isReady();
        const emailMonitorReady = await this.emailMonitorService.isReady();
        const virusScannerReady = await this.virusScannerService.isReady();

        const allReady = storageReady && queueReady && emailMonitorReady && virusScannerReady;
        const details = {
          storage: storageReady ? 'UP' : 'DOWN',
          messageQueue: queueReady ? 'UP' : 'DOWN',
          emailMonitor: emailMonitorReady ? 'UP' : 'DOWN',
          virusScanner: virusScannerReady ? 'UP' : 'DOWN'
        };

        if (allReady) {
          res.status(200).json({
            status: 'UP',
            timestamp: new Date().toISOString(),
            service: appConfig.serviceName,
            version: appConfig.version,
            details
          });
        } else {
          res.status(503).json({
            status: 'DOWN',
            timestamp: new Date().toISOString(),
            service: appConfig.serviceName,
            version: appConfig.version,
            details
          });
        }
      } catch (error) {
        this.logger.error('Health check failed', error);
        res.status(500).json({ 
          status: 'ERROR', 
          timestamp: new Date().toISOString(),
          service: appConfig.serviceName,
          version: appConfig.version,
          error: 'Health check failed' 
        });
      }
    });
    
    // Startup probe for Kubernetes to determine when the application is fully initialized
    this.app.get('/health/startup', (req: Request, res: Response) => {
      if (this.emailMonitorService.isMonitoring()) {
        res.status(200).json({ 
          status: 'UP',
          timestamp: new Date().toISOString(),
          service: appConfig.serviceName,
          version: appConfig.version,
          message: 'Email monitoring is active'
        });
      } else {
        res.status(503).json({ 
          status: 'DOWN',
          timestamp: new Date().toISOString(),
          service: appConfig.serviceName,
          version: appConfig.version,
          message: 'Email monitoring not yet active'
        });
      }
    });
  }

  /**
   * Starts the application and all its services
   * Connects to external dependencies and begins email monitoring
   * @returns Promise that resolves when the application has started successfully
   */
  public async start(): Promise<void> {
    if (this.server) {
      this.logger.warn('Application is already running');
      return;
    }
    
    try {
      this.logger.info('Starting application services...');
      
      // Initialize and connect services in the correct order with timeouts
      const connectWithTimeout = async <T>(promise: Promise<T>, serviceName: string, timeoutMs: number): Promise<T> => {
        let timeoutId: NodeJS.Timeout;
        const timeoutPromise = new Promise<never>((_, reject) => {
          timeoutId = setTimeout(() => {
            reject(new Error(`Connection to ${serviceName} timed out after ${timeoutMs}ms`));
          }, timeoutMs);
        });
        
        try {
          const result = await Promise.race([promise, timeoutPromise]);
          clearTimeout(timeoutId!);
          return result as T;
        } catch (error) {
          clearTimeout(timeoutId!);
          throw error;
        }
      };
      
      // Connect to storage service (S3)
      await connectWithTimeout(
        this.storageService.connect(),
        'storage service',
        10000 // 10 seconds timeout
      );
      this.logger.info('Storage service connected');
      
      // Connect to message queue (RabbitMQ)
      await connectWithTimeout(
        this.messageQueueService.connect(),
        'message queue service',
        15000 // 15 seconds timeout
      );
      this.logger.info('Message queue service connected');
      
      // Initialize virus scanner
      await connectWithTimeout(
        this.virusScannerService.initialize(),
        'virus scanner service',
        10000 // 10 seconds timeout
      );
      this.logger.info('Virus scanner service initialized');
      
      // Connect to email server (IMAP)
      await connectWithTimeout(
        this.emailMonitorService.connect(),
        'email monitor service',
        20000 // 20 seconds timeout
      );
      this.logger.info('Email monitor service connected');
      
      // Start the email monitoring process
      await this.emailMonitorService.startMonitoring();
      this.logger.info('Email monitoring started');
      
      // Start the HTTP server
      const port = appConfig.port || 3000;
      this.server = this.app.listen(port, () => {
        this.logger.info(`Server listening on port ${port}`);
      });

      // Handle graceful shutdown
      this.setupGracefulShutdown();
      
      this.logger.info(`${appConfig.serviceName} v${appConfig.version} started successfully in ${appConfig.environment} environment`);
    } catch (error) {
      this.logger.error('Failed to start application', error);
      // Attempt to clean up any partially initialized services
      await this.stop().catch(stopError => {
        this.logger.error('Failed to clean up after startup failure', stopError);
      });
      throw error;
    }
  }

  /**
   * Stops the application and all its services gracefully
   */
  public async stop(): Promise<void> {
    if (this.isShuttingDown) {
      return;
    }
    
    this.isShuttingDown = true;
    this.logger.info('Stopping application...');

    try {
      // Stop services in reverse order of initialization
      if (this.emailMonitorService) {
        await this.emailMonitorService.stopMonitoring();
        await this.emailMonitorService.disconnect();
        this.logger.info('Email monitor service stopped');
      }

      if (this.messageQueueService) {
        await this.messageQueueService.disconnect();
        this.logger.info('Message queue service disconnected');
      }

      if (this.storageService) {
        await this.storageService.disconnect();
        this.logger.info('Storage service disconnected');
      }

      // Close the HTTP server
      if (this.server) {
        await new Promise<void>((resolve, reject) => {
          this.server?.close((err) => {
            if (err) {
              reject(err);
            } else {
              resolve();
            }
          });
        });
        this.logger.info('HTTP server closed');
      }

      this.logger.info(`${appConfig.serviceName} stopped successfully`);
    } catch (error) {
      this.logger.error('Error during application shutdown', error);
      throw error;
    }
  }

  /**
   * Sets up handlers for graceful shutdown on process signals
   */
  private setupGracefulShutdown(): void {
    const signals = ['SIGINT', 'SIGTERM', 'SIGQUIT'];
    
    signals.forEach((signal) => {
      process.on(signal, async () => {
        this.logger.info(`Received ${signal} signal, shutting down gracefully`);
        try {
          await this.stop();
          process.exit(0);
        } catch (error) {
          this.logger.error('Error during graceful shutdown', error);
          process.exit(1);
        }
      });
    });

    // Handle uncaught exceptions and unhandled rejections
    process.on('uncaughtException', (error) => {
      this.logger.error('Uncaught exception', error);
      this.performEmergencyShutdown(1);
    });

    process.on('unhandledRejection', (reason) => {
      this.logger.error('Unhandled rejection', reason);
      this.performEmergencyShutdown(1);
    });
  }

  /**
   * Performs an emergency shutdown when an unrecoverable error occurs
   * @param exitCode The process exit code
   */
  private performEmergencyShutdown(exitCode: number): void {
    this.logger.error(`Performing emergency shutdown with exit code ${exitCode}`);
    try {
      // Attempt to stop services, but exit regardless after timeout
      const shutdownTimeout = setTimeout(() => {
        this.logger.error('Emergency shutdown timeout reached, forcing exit');
        process.exit(exitCode);
      }, 5000);

      this.stop().finally(() => {
        clearTimeout(shutdownTimeout);
        process.exit(exitCode);
      });
    } catch (error) {
      this.logger.error('Error during emergency shutdown', error);
      process.exit(exitCode);
    }
  }
}

/**
 * Create and export the application instance
 * This singleton instance can be imported and used throughout the application
 */
export const application = new Application();

/**
 * If this file is executed directly (e.g., with `node dist/app.js`),
 * start the application automatically
 */
if (require.main === module) {
  application.start().catch((error) => {
    console.error('Failed to start application:', error);
    process.exit(1);
  });
}