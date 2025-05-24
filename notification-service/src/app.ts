import express, { Application, Request, Response, NextFunction } from 'express';
import helmet from 'helmet';
import cors from 'cors';
import { createServer, Server } from 'http';
import { connect, Connection, Channel } from 'amqplib';
import { Redis } from 'ioredis';

// Import configuration
import { appConfig, rabbitMQConfig, redisConfig } from './config';
import { configureLogger, logger } from './config/logger';

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
  registerMiddleware,
  correlationMiddleware,
  loggingMiddleware,
  errorMiddleware
} from './middleware';

// Import routes
import { webhookRoutes, healthRoutes, statusRoutes } from './routes';

// Import types
import { INotification, IRabbitMQConnection } from './types';

/**
 * Main application class for the Notification Service
 * 
 * This class is responsible for:
 * - Initializing the Express application
 * - Configuring middleware and routes
 * - Establishing connections to RabbitMQ and Redis
 * - Creating service instances
 * - Managing application lifecycle (start/stop)
 */
export class App {
  private app: Application;
  private server: Server | null = null;
  private rabbitConnection: Connection | null = null;
  private rabbitChannel: Channel | null = null;
  private redisClient: Redis | null = null;
  
  // Service instances
  private notificationService: NotificationService | null = null;
  private webhookService: WebhookService | null = null;
  private retryService: RetryService | null = null;
  private auditService: AuditService | null = null;
  private messageService: MessageService | null = null;
  
  // Application state
  private isShuttingDown = false;
  private healthStatus = {
    status: 'starting',
    rabbitmq: false,
    redis: false,
    services: false
  };

  /**
   * Constructor initializes the Express application and configures middleware
   */
  constructor() {
    // Initialize logger with configured log levels
    configureLogger(appConfig.environment);
    logger.info(`Initializing Notification Service in ${appConfig.environment} environment`);
    
    // Create Express application
    this.app = express();
    
    // Configure basic middleware
    this.app.use(helmet());
    this.app.use(cors());
    this.app.use(express.json());
    this.app.use(express.urlencoded({ extended: true }));
    
    // Add correlation ID middleware for request tracking
    this.app.use(correlationMiddleware());
    
    // Add request logging middleware
    this.app.use(loggingMiddleware());
    
    // Register all middleware
    registerMiddleware(this.app);
    
    // Configure routes
    this.configureRoutes();
    
    // Add error handling middleware (must be last)
    this.app.use(errorMiddleware());
  }

  /**
   * Configure application routes
   */
  private configureRoutes(): void {
    // Health check routes (no auth required)
    this.app.use('/health', healthRoutes);
    
    // API routes
    this.app.use('/api/v1/webhooks', webhookRoutes);
    this.app.use('/api/v1/notifications', statusRoutes);
    
    // Basic root endpoint
    this.app.get('/', (req: Request, res: Response) => {
      res.json({
        service: 'Notification Service',
        version: appConfig.version,
        status: 'running'
      });
    });
    
    // 404 handler
    this.app.use((req: Request, res: Response) => {
      res.status(404).json({ error: 'Not Found' });
    });
  }

  /**
   * Connect to RabbitMQ message broker
   */
  private async connectToRabbitMQ(): Promise<void> {
    try {
      logger.info('Connecting to RabbitMQ...');
      
      // Create connection with TLS options
      const connectionOptions: IRabbitMQConnection = {
        protocol: rabbitMQConfig.protocol,
        hostname: rabbitMQConfig.host,
        port: rabbitMQConfig.port,
        username: rabbitMQConfig.username,
        password: rabbitMQConfig.password,
        vhost: rabbitMQConfig.vhost,
        ...(rabbitMQConfig.useTLS && {
          cert: rabbitMQConfig.certPath,
          key: rabbitMQConfig.keyPath,
          ca: [rabbitMQConfig.caPath],
          passphrase: rabbitMQConfig.certPassphrase
        })
      };
      
      this.rabbitConnection = await connect(connectionOptions);
      
      // Handle connection errors and closure
      this.rabbitConnection.on('error', (err) => {
        logger.error('RabbitMQ connection error', { error: err.message });
        this.healthStatus.rabbitmq = false;
        
        if (!this.isShuttingDown) {
          setTimeout(() => this.connectToRabbitMQ(), 5000);
        }
      });
      
      this.rabbitConnection.on('close', () => {
        logger.warn('RabbitMQ connection closed');
        this.healthStatus.rabbitmq = false;
        
        if (!this.isShuttingDown) {
          setTimeout(() => this.connectToRabbitMQ(), 5000);
        }
      });
      
      // Create channel
      this.rabbitChannel = await this.rabbitConnection.createChannel();
      
      // Ensure queue exists
      await this.rabbitChannel.assertQueue(rabbitMQConfig.queue, {
        durable: true,
        arguments: {
          'x-dead-letter-exchange': rabbitMQConfig.deadLetterExchange,
          'x-dead-letter-routing-key': rabbitMQConfig.deadLetterRoutingKey
        }
      });
      
      // Ensure dead letter queue exists
      await this.rabbitChannel.assertQueue(rabbitMQConfig.deadLetterQueue, {
        durable: true
      });
      
      // Ensure dead letter exchange exists
      await this.rabbitChannel.assertExchange(
        rabbitMQConfig.deadLetterExchange,
        'direct',
        { durable: true }
      );
      
      // Bind dead letter queue to exchange
      await this.rabbitChannel.bindQueue(
        rabbitMQConfig.deadLetterQueue,
        rabbitMQConfig.deadLetterExchange,
        rabbitMQConfig.deadLetterRoutingKey
      );
      
      logger.info('Successfully connected to RabbitMQ');
      this.healthStatus.rabbitmq = true;
    } catch (error) {
      logger.error('Failed to connect to RabbitMQ', { error: (error as Error).message });
      this.healthStatus.rabbitmq = false;
      
      if (!this.isShuttingDown) {
        setTimeout(() => this.connectToRabbitMQ(), 5000);
      }
    }
  }

  /**
   * Connect to Redis cache
   */
  private async connectToRedis(): Promise<void> {
    try {
      logger.info('Connecting to Redis...');
      
      // Create Redis client with TLS if configured
      this.redisClient = new Redis({
        host: redisConfig.host,
        port: redisConfig.port,
        password: redisConfig.password,
        db: redisConfig.db,
        keyPrefix: redisConfig.keyPrefix,
        retryStrategy: (times) => {
          if (this.isShuttingDown) return null;
          return Math.min(times * 100, 3000);
        },
        ...(redisConfig.useTLS && {
          tls: {
            ca: redisConfig.caPath,
            cert: redisConfig.certPath,
            key: redisConfig.keyPath,
            passphrase: redisConfig.certPassphrase,
            rejectUnauthorized: true
          }
        })
      });
      
      // Handle Redis events
      this.redisClient.on('connect', () => {
        logger.info('Connected to Redis');
        this.healthStatus.redis = true;
      });
      
      this.redisClient.on('error', (err) => {
        logger.error('Redis connection error', { error: err.message });
        this.healthStatus.redis = false;
      });
      
      this.redisClient.on('close', () => {
        logger.warn('Redis connection closed');
        this.healthStatus.redis = false;
      });
      
      // Test connection
      await this.redisClient.ping();
      logger.info('Successfully connected to Redis');
      this.healthStatus.redis = true;
    } catch (error) {
      logger.error('Failed to connect to Redis', { error: (error as Error).message });
      this.healthStatus.redis = false;
      
      if (!this.isShuttingDown) {
        setTimeout(() => this.connectToRedis(), 5000);
      }
    }
  }

  /**
   * Initialize service instances
   */
  private initializeServices(): void {
    try {
      logger.info('Initializing services...');
      
      if (!this.rabbitChannel || !this.redisClient) {
        throw new Error('Cannot initialize services: RabbitMQ or Redis not connected');
      }
      
      // Create service instances
      this.auditService = new AuditService(this.redisClient);
      this.retryService = new RetryService(this.redisClient, this.auditService);
      this.messageService = new MessageService(this.auditService);
      this.webhookService = new WebhookService(this.retryService, this.auditService);
      
      // Create notification service (depends on other services)
      this.notificationService = new NotificationService(
        this.rabbitChannel,
        this.webhookService,
        this.messageService,
        this.auditService
      );
      
      logger.info('Services initialized successfully');
      this.healthStatus.services = true;
    } catch (error) {
      logger.error('Failed to initialize services', { error: (error as Error).message });
      this.healthStatus.services = false;
      throw error;
    }
  }

  /**
   * Start consuming messages from RabbitMQ
   */
  private startConsumingMessages(): void {
    if (!this.rabbitChannel || !this.notificationService) {
      logger.error('Cannot start consuming messages: RabbitMQ channel or NotificationService not initialized');
      return;
    }
    
    try {
      logger.info(`Starting to consume messages from queue: ${rabbitMQConfig.queue}`);
      
      // Start consuming messages
      this.rabbitChannel.consume(
        rabbitMQConfig.queue,
        (msg) => {
          if (msg) {
            try {
              // Parse message content
              const content = msg.content.toString();
              const notification = JSON.parse(content) as INotification;
              
              // Process notification
              this.notificationService?.processNotification(notification, msg)
                .catch((error) => {
                  logger.error('Error processing notification', {
                    error: error.message,
                    notificationId: notification.id
                  });
                  
                  // Reject message if processing fails
                  this.rabbitChannel?.reject(msg, false);
                });
            } catch (error) {
              logger.error('Error parsing message', { error: (error as Error).message });
              
              // Reject malformed messages
              this.rabbitChannel?.reject(msg, false);
            }
          }
        },
        { noAck: false } // Manual acknowledgment
      );
      
      logger.info('Successfully started consuming messages');
    } catch (error) {
      logger.error('Failed to start consuming messages', { error: (error as Error).message });
      
      if (!this.isShuttingDown) {
        setTimeout(() => this.startConsumingMessages(), 5000);
      }
    }
  }

  /**
   * Update health check status
   */
  private updateHealthStatus(): void {
    const allServicesHealthy = this.healthStatus.rabbitmq && 
                              this.healthStatus.redis && 
                              this.healthStatus.services;
    
    this.healthStatus.status = this.isShuttingDown ? 'shutting_down' :
                              allServicesHealthy ? 'healthy' : 'unhealthy';
  }

  /**
   * Get current health status
   */
  public getHealthStatus() {
    this.updateHealthStatus();
    return {
      ...this.healthStatus,
      uptime: process.uptime(),
      timestamp: new Date().toISOString(),
      version: appConfig.version,
      environment: appConfig.environment
    };
  }

  /**
   * Start the application
   */
  public async start(): Promise<void> {
    try {
      logger.info('Starting Notification Service...');
      
      // Connect to external services
      await Promise.all([
        this.connectToRabbitMQ(),
        this.connectToRedis()
      ]);
      
      // Initialize services
      this.initializeServices();
      
      // Start HTTP server
      this.server = createServer(this.app);
      this.server.listen(appConfig.port, () => {
        logger.info(`Notification Service listening on port ${appConfig.port}`);
      });
      
      // Start consuming messages
      this.startConsumingMessages();
      
      // Update health status
      this.updateHealthStatus();
      
      logger.info('Notification Service started successfully');
    } catch (error) {
      logger.error('Failed to start Notification Service', { error: (error as Error).message });
      throw error;
    }
  }

  /**
   * Stop the application gracefully
   */
  public async stop(): Promise<void> {
    if (this.isShuttingDown) return;
    
    this.isShuttingDown = true;
    logger.info('Shutting down Notification Service...');
    
    // Update health status
    this.updateHealthStatus();
    
    try {
      // Close HTTP server
      if (this.server) {
        await new Promise<void>((resolve, reject) => {
          this.server?.close((err) => {
            if (err) reject(err);
            else resolve();
          });
        });
        logger.info('HTTP server closed');
      }
      
      // Close RabbitMQ connection
      if (this.rabbitChannel) {
        await this.rabbitChannel.close();
        logger.info('RabbitMQ channel closed');
      }
      
      if (this.rabbitConnection) {
        await this.rabbitConnection.close();
        logger.info('RabbitMQ connection closed');
      }
      
      // Close Redis connection
      if (this.redisClient) {
        await this.redisClient.quit();
        logger.info('Redis connection closed');
      }
      
      logger.info('Notification Service shut down successfully');
    } catch (error) {
      logger.error('Error during shutdown', { error: (error as Error).message });
      throw error;
    }
  }

  /**
   * Get Express application instance
   */
  public getApp(): Application {
    return this.app;
  }
}

// Export a singleton instance
export default new App();