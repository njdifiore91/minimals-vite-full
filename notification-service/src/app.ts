import express, { Application as ExpressApplication, Request, Response, NextFunction } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import { Server } from 'http';

// Import configuration
import { appConfig, loggerConfig, rabbitMQConfig, redisConfig, webhookConfig } from './config';

// Import services
import {
  NotificationService,
  WebhookService,
  RetryService,
  AuditService,
  MessageService
} from './services';

// Import middleware
import {
  correlationMiddleware,
  loggingMiddleware,
  errorMiddleware,
  authMiddleware,
  validationMiddleware,
  rateLimitMiddleware
} from './middleware';

// Import routes
import { healthRoutes, webhookRoutes, statusRoutes } from './routes';

// Import types
import { IServiceStatus } from './types/common';
import { ILogContext } from './types/common';

// Import logger
import logger from './config/logger';

/**
 * Main Application class for the Notification Service
 * Manages the lifecycle of the service and coordinates all components
 */
export class Application {
  private static instance: Application;
  private express: ExpressApplication;
  private server: Server | null = null;
  private isShuttingDown = false;
  
  // Service instances
  private notificationService: NotificationService;
  private webhookService: WebhookService;
  private retryService: RetryService;
  private auditService: AuditService;
  private messageService: MessageService;

  /**
   * Private constructor to enforce singleton pattern
   */
  private constructor() {
    // Initialize Express application
    this.express = express();
    
    // Initialize services
    this.notificationService = new NotificationService();
    this.webhookService = new WebhookService();
    this.retryService = new RetryService();
    this.auditService = new AuditService();
    this.messageService = new MessageService();
    
    // Configure Express middleware
    this.configureMiddleware();
    
    // Configure Express routes
    this.configureRoutes();
  }

  /**
   * Get the singleton instance of the Application
   * @returns Application instance
   */
  public static getInstance(): Application {
    if (!Application.instance) {
      Application.instance = new Application();
    }
    return Application.instance;
  }

  /**
   * Configure Express middleware
   */
  private configureMiddleware(): void {
    // Security middleware
    this.express.use(helmet());
    
    // CORS configuration
    this.express.use(cors({
      origin: appConfig.corsOrigins,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Correlation-ID'],
      credentials: true,
      maxAge: 86400 // 24 hours
    }));
    
    // Request parsing
    this.express.use(express.json({ limit: '1mb' }));
    this.express.use(express.urlencoded({ extended: true, limit: '1mb' }));
    
    // Compression
    this.express.use(compression());
    
    // Custom middleware
    this.express.use(correlationMiddleware());
    this.express.use(loggingMiddleware(loggerConfig));
    
    // Rate limiting for API endpoints
    this.express.use('/api', rateLimitMiddleware(redisConfig));
    
    // Authentication for protected routes
    this.express.use('/api/webhooks', authMiddleware());
  }

  /**
   * Configure Express routes
   */
  private configureRoutes(): void {
    // Health check routes - no auth required
    this.express.use('/health', healthRoutes);
    
    // API routes - with auth
    this.express.use('/api/webhooks', webhookRoutes);
    this.express.use('/api/notifications', statusRoutes);
    
    // Basic root endpoint
    this.express.get('/', (req: Request, res: Response) => {
      res.status(200).json({
        service: 'Notification Service',
        version: appConfig.version,
        status: 'running'
      });
    });
    
    // 404 handler
    this.express.use((req: Request, res: Response) => {
      res.status(404).json({
        error: 'Not Found',
        message: `Route ${req.method} ${req.path} not found`,
        status: 404
      });
    });
    
    // Error middleware should be registered last
    this.express.use(errorMiddleware());
  }

  /**
   * Start the application
   * @returns Promise that resolves when the application has started
   */
  public async start(): Promise<void> {
    try {
      logger.info('Starting Notification Service...');
      
      // Initialize services
      await this.initializeServices();
      
      // Start HTTP server
      await this.startServer();
      
      logger.info(`Notification Service started successfully on port ${appConfig.port}`);
    } catch (error) {
      logger.error('Failed to start Notification Service', { error });
      throw error;
    }
  }

  /**
   * Initialize all required services
   * @returns Promise that resolves when all services are initialized
   */
  private async initializeServices(): Promise<void> {
    try {
      logger.info('Initializing services...');
      
      // Initialize Redis connection
      logger.info('Connecting to Redis...');
      // Redis initialization would happen here
      
      // Initialize RabbitMQ connection
      logger.info('Connecting to RabbitMQ...');
      await this.notificationService.initialize(rabbitMQConfig);
      
      // Initialize webhook service
      logger.info('Initializing webhook service...');
      await this.webhookService.initialize(webhookConfig);
      
      // Initialize retry service
      logger.info('Initializing retry service...');
      await this.retryService.initialize();
      
      // Initialize audit service
      logger.info('Initializing audit service...');
      await this.auditService.initialize();
      
      // Initialize message service
      logger.info('Initializing message service...');
      await this.messageService.initialize();
      
      logger.info('All services initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize services', { error });
      throw error;
    }
  }

  /**
   * Start the HTTP server
   * @returns Promise that resolves when the server has started
   */
  private startServer(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.server = this.express.listen(appConfig.port, () => {
          logger.info(`HTTP server listening on port ${appConfig.port}`);
          resolve();
        });
        
        // Handle server errors
        this.server.on('error', (error) => {
          logger.error('HTTP server error', { error });
          reject(error);
        });
      } catch (error) {
        logger.error('Failed to start HTTP server', { error });
        reject(error);
      }
    });
  }

  /**
   * Stop the application gracefully
   * @returns Promise that resolves when the application has stopped
   */
  public async stop(): Promise<void> {
    if (this.isShuttingDown) {
      logger.info('Shutdown already in progress');
      return;
    }
    
    this.isShuttingDown = true;
    logger.info('Stopping Notification Service...');
    
    try {
      // Stop HTTP server first to stop accepting new requests
      if (this.server) {
        await this.stopServer();
      }
      
      // Stop services
      await this.stopServices();
      
      logger.info('Notification Service stopped successfully');
    } catch (error) {
      logger.error('Error during shutdown', { error });
      // Force exit in case of shutdown errors
      process.exit(1);
    }
  }

  /**
   * Stop the HTTP server gracefully
   * @returns Promise that resolves when the server has stopped
   */
  private stopServer(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.server) {
        resolve();
        return;
      }
      
      logger.info('Stopping HTTP server...');
      this.server.close((error) => {
        if (error) {
          logger.error('Error closing HTTP server', { error });
          reject(error);
          return;
        }
        
        logger.info('HTTP server stopped successfully');
        this.server = null;
        resolve();
      });
    });
  }

  /**
   * Stop all services gracefully
   * @returns Promise that resolves when all services have stopped
   */
  private async stopServices(): Promise<void> {
    try {
      logger.info('Stopping services...');
      
      // Stop notification service (RabbitMQ consumer)
      logger.info('Stopping notification service...');
      await this.notificationService.shutdown();
      
      // Stop webhook service
      logger.info('Stopping webhook service...');
      await this.webhookService.shutdown();
      
      // Stop retry service
      logger.info('Stopping retry service...');
      await this.retryService.shutdown();
      
      // Stop audit service
      logger.info('Stopping audit service...');
      await this.auditService.shutdown();
      
      // Stop message service
      logger.info('Stopping message service...');
      await this.messageService.shutdown();
      
      logger.info('All services stopped successfully');
    } catch (error) {
      logger.error('Error stopping services', { error });
      throw error;
    }
  }

  /**
   * Get the Express application instance
   * @returns Express application
   */
  public getExpressApp(): ExpressApplication {
    return this.express;
  }

  /**
   * Get the health status of the application
   * @returns Health status object
   */
  public async getHealthStatus(): Promise<IServiceStatus> {
    const rabbitMQStatus = await this.notificationService.checkHealth();
    const webhookStatus = await this.webhookService.checkHealth();
    const retryStatus = await this.retryService.checkHealth();
    
    const isHealthy = rabbitMQStatus.healthy && webhookStatus.healthy && retryStatus.healthy;
    
    return {
      service: 'notification-service',
      version: appConfig.version,
      healthy: isHealthy,
      timestamp: new Date().toISOString(),
      dependencies: {
        rabbitMQ: rabbitMQStatus,
        webhookService: webhookStatus,
        retryService: retryStatus
      }
    };
  }
}

// Export default instance
export default Application.getInstance();