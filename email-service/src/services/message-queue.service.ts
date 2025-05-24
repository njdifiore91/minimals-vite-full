/**
 * Message Queue Service
 * 
 * Manages the connection to RabbitMQ and handles publishing messages about new documents
 * to the message queue. This service is crucial for communication between the Email Service
 * and other microservices in the system.
 * 
 * Features:
 * - Secure connection with TLS and client certificate authentication
 * - Publishing to the 'mca.documents' exchange (fanout)
 * - Message serialization in standardized JSON format
 * - Retry logic with configurable backoff periods
 * - Connection error handling and recovery strategies
 * - Graceful shutdown and reconnection
 */

import amqp, { Channel, Connection, Options } from 'amqplib';
import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';

import { 
  rabbitMQConfig, 
  mcaDocumentsExchange, 
  publishOptions, 
  retryConfig 
} from '../config/rabbitmq';
import { 
  ConnectionState, 
  ConnectionEventType, 
  IMessagePayload, 
  IPublishOptions, 
  IExchangeConfig 
} from '../types/message-queue';
import { createComponentLogger, logError } from '../config/logger';
import { 
  withRetry, 
  RABBITMQ_RETRY_OPTIONS, 
  RetryOptions, 
  RetryableErrorType 
} from '../utils/retry';

/**
 * Message Queue Service class
 * 
 * Manages RabbitMQ connections and provides methods for publishing messages
 * to the document processing exchange.
 */
export class MessageQueueService extends EventEmitter {
  private connection: Connection | null = null;
  private channel: Channel | null = null;
  private connectionState: ConnectionState = ConnectionState.DISCONNECTED;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private readonly logger = createComponentLogger('MessageQueueService');
  private readonly config = rabbitMQConfig;
  private readonly exchange: IExchangeConfig;
  private readonly publishOpts: IPublishOptions;
  private readonly retryOpts: RetryOptions;
  
  /**
   * Creates a new MessageQueueService instance
   * 
   * @param exchangeConfig - Optional custom exchange configuration
   * @param publishOptions - Optional custom publish options
   * @param retryOptions - Optional custom retry options
   */
  constructor(
    exchangeConfig: IExchangeConfig = mcaDocumentsExchange,
    publishOpts: IPublishOptions = publishOptions,
    retryOpts: RetryOptions = RABBITMQ_RETRY_OPTIONS
  ) {
    super();
    this.exchange = exchangeConfig;
    this.publishOpts = publishOpts;
    this.retryOpts = retryOpts;
    
    // Set up event listeners for connection events
    this.on(ConnectionEventType.CONNECTED, () => {
      this.logger.info('Connected to RabbitMQ server', { 
        host: this.config.host, 
        port: this.config.port,
        vhost: this.config.vhost,
        exchange: this.exchange.name
      });
    });
    
    this.on(ConnectionEventType.DISCONNECTED, (error?: Error) => {
      if (error) {
        logError(this.logger, 'Disconnected from RabbitMQ server with error', error, {
          host: this.config.host,
          port: this.config.port
        });
      } else {
        this.logger.info('Disconnected from RabbitMQ server', { 
          host: this.config.host, 
          port: this.config.port 
        });
      }
    });
    
    this.on(ConnectionEventType.ERROR, (error: Error) => {
      logError(this.logger, 'RabbitMQ connection error', error, {
        host: this.config.host,
        port: this.config.port,
        connectionState: this.connectionState
      });
    });
    
    this.on(ConnectionEventType.BLOCKED, (reason: string) => {
      this.logger.warn('RabbitMQ connection blocked', { 
        reason, 
        host: this.config.host, 
        port: this.config.port 
      });
    });
    
    this.on(ConnectionEventType.UNBLOCKED, () => {
      this.logger.info('RabbitMQ connection unblocked', { 
        host: this.config.host, 
        port: this.config.port 
      });
    });
  }
  
  /**
   * Connects to the RabbitMQ server
   * 
   * @returns A promise that resolves when connected
   */
  public async connect(): Promise<void> {
    if (
      this.connectionState === ConnectionState.CONNECTED ||
      this.connectionState === ConnectionState.CONNECTING
    ) {
      this.logger.debug('Already connected or connecting to RabbitMQ');
      return;
    }
    
    this.connectionState = ConnectionState.CONNECTING;
    this.logger.info('Connecting to RabbitMQ server', { 
      host: this.config.host, 
      port: this.config.port,
      vhost: this.config.vhost,
      useTls: this.config.useTls
    });
    
    try {
      // Build connection URL
      const protocol = this.config.useTls ? 'amqps' : 'amqp';
      const auth = `${encodeURIComponent(this.config.username)}:${encodeURIComponent(this.config.password)}`;
      const vhost = encodeURIComponent(this.config.vhost);
      const connectionUrl = `${protocol}://${auth}@${this.config.host}:${this.config.port}/${vhost}`;
      
      // Connection options
      const socketOptions: any = {
        servername: this.config.host, // Required for SNI (Server Name Indication)
      };
      
      // Add TLS options if enabled
      if (this.config.useTls && this.config.tlsOptions) {
        Object.assign(socketOptions, this.config.tlsOptions);
      }
      
      const connectionOptions: Options.Connect = {
        timeout: this.config.connectionTimeout,
        heartbeat: this.config.heartbeat,
        socket: socketOptions,
      };
      
      // Connect to RabbitMQ with retry logic
      const result = await withRetry(
        async () => amqp.connect(connectionUrl, connectionOptions),
        {
          ...this.retryOpts,
          onRetry: (attempt, delay, error) => {
            this.logger.warn(
              `Retrying RabbitMQ connection (attempt ${attempt}/${this.retryOpts.maxRetries}) after ${delay}ms`,
              { error: error.message, host: this.config.host, port: this.config.port }
            );
          },
        }
      );
      
      if (!result.success || !result.result) {
        throw result.error || new Error('Failed to connect to RabbitMQ');
      }
      
      this.connection = result.result;
      
      // Set up connection event handlers
      this.connection.on('error', (err) => {
        const error = err as Error;
        this.emit(ConnectionEventType.ERROR, error);
        
        // Only attempt reconnection if not closing/closed
        if (
          this.connectionState !== ConnectionState.CLOSING &&
          this.connectionState !== ConnectionState.CLOSED
        ) {
          this.handleConnectionFailure(error);
        }
      });
      
      this.connection.on('close', (err?: Error) => {
        this.channel = null;
        this.connectionState = ConnectionState.DISCONNECTED;
        this.emit(ConnectionEventType.DISCONNECTED, err);
        
        // Only attempt reconnection if not closing/closed
        if (
          this.connectionState !== ConnectionState.CLOSING &&
          this.connectionState !== ConnectionState.CLOSED
        ) {
          this.handleConnectionFailure(err);
        }
      });
      
      this.connection.on('blocked', (reason: string) => {
        this.emit(ConnectionEventType.BLOCKED, reason);
      });
      
      this.connection.on('unblocked', () => {
        this.emit(ConnectionEventType.UNBLOCKED);
      });
      
      // Create a channel
      await this.createChannel();
      
      // Update connection state
      this.connectionState = ConnectionState.CONNECTED;
      this.emit(ConnectionEventType.CONNECTED);
      
    } catch (error) {
      this.connectionState = ConnectionState.DISCONNECTED;
      const err = error instanceof Error ? error : new Error(String(error));
      logError(this.logger, 'Failed to connect to RabbitMQ', err, {
        host: this.config.host,
        port: this.config.port,
      });
      
      this.handleConnectionFailure(err);
      throw err;
    }
  }
  
  /**
   * Creates a channel and sets up the exchange
   * 
   * @returns A promise that resolves when the channel is created
   */
  private async createChannel(): Promise<void> {
    if (!this.connection) {
      throw new Error('Cannot create channel: No RabbitMQ connection');
    }
    
    try {
      // Create a channel
      this.channel = await this.connection.createChannel();
      
      // Set up channel error handler
      this.channel.on('error', (err) => {
        const error = err as Error;
        logError(this.logger, 'RabbitMQ channel error', error);
        
        // Attempt to recreate the channel
        this.channel = null;
        this.createChannel().catch((channelError) => {
          logError(this.logger, 'Failed to recreate RabbitMQ channel', channelError);
        });
      });
      
      this.channel.on('close', () => {
        this.logger.info('RabbitMQ channel closed');
        this.channel = null;
      });
      
      // Assert exchange
      await this.channel.assertExchange(
        this.exchange.name,
        this.exchange.type,
        {
          durable: this.exchange.durable,
          autoDelete: this.exchange.autoDelete,
          arguments: this.exchange.arguments,
        }
      );
      
      this.logger.info('RabbitMQ channel created and exchange asserted', {
        exchange: this.exchange.name,
        type: this.exchange.type,
      });
      
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      logError(this.logger, 'Failed to create RabbitMQ channel', err);
      this.channel = null;
      throw err;
    }
  }
  
  /**
   * Handles connection failures and implements reconnection strategy
   * 
   * @param error - The error that caused the connection failure
   */
  private handleConnectionFailure(error?: Error): void {
    // Clear any existing reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    // Set connection state to reconnecting
    this.connectionState = ConnectionState.RECONNECTING;
    
    // Calculate reconnect delay with exponential backoff and jitter
    const reconnectDelay = Math.floor(
      1000 * Math.random() + 5000
    ); // Random delay between 1-6 seconds
    
    this.logger.info('Scheduling RabbitMQ reconnection', {
      delay: reconnectDelay,
      error: error?.message,
    });
    
    // Schedule reconnection
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.logger.info('Attempting to reconnect to RabbitMQ');
      
      this.connect().catch((reconnectError) => {
        logError(this.logger, 'Failed to reconnect to RabbitMQ', reconnectError);
        // The connect method will handle scheduling the next reconnection attempt
      });
    }, reconnectDelay);
  }
  
  /**
   * Publishes a message to the RabbitMQ exchange
   * 
   * @param payload - The message payload to publish
   * @param routingKey - Optional routing key (default: '')
   * @param options - Optional publish options to override defaults
   * @returns A promise that resolves when the message is published
   */
  public async publishMessage(
    payload: IMessagePayload,
    routingKey: string = '',
    options?: Partial<IPublishOptions>
  ): Promise<boolean> {
    // Ensure we have a connection and channel
    if (!this.connection || !this.channel) {
      this.logger.warn('Attempting to publish without an active connection, connecting first');
      await this.connect();
    }
    
    // If we still don't have a channel after connecting, throw an error
    if (!this.channel) {
      throw new Error('Failed to create channel for publishing');
    }
    
    try {
      // Merge default options with provided options
      const publishOpts: IPublishOptions = {
        ...this.publishOpts,
        ...options,
        // Add message ID if not provided
        messageId: options?.messageId || payload.id || uuidv4(),
        // Add timestamp if not provided
        timestamp: options?.timestamp || Math.floor(Date.now() / 1000),
      };
      
      // Serialize the payload to a Buffer
      const content = Buffer.from(JSON.stringify(payload));
      
      // Publish with retry logic
      const result = await withRetry(
        async () => {
          const published = this.channel!.publish(
            this.exchange.name,
            routingKey,
            content,
            publishOpts
          );
          
          if (!published) {
            // Channel is experiencing backpressure, wait for drain event
            await new Promise<void>((resolve, reject) => {
              const timeout = setTimeout(() => {
                this.channel!.removeListener('drain', onDrain);
                reject(new Error('Timeout waiting for drain event'));
              }, 30000); // 30 second timeout
              
              const onDrain = () => {
                clearTimeout(timeout);
                resolve();
              };
              
              this.channel!.once('drain', onDrain);
            });
          }
          
          return true;
        },
        {
          ...this.retryOpts,
          onRetry: (attempt, delay, error) => {
            this.logger.warn(
              `Retrying message publication (attempt ${attempt}/${this.retryOpts.maxRetries}) after ${delay}ms`,
              { 
                error: error.message, 
                exchange: this.exchange.name,
                routingKey,
                messageId: publishOpts.messageId 
              }
            );
          },
        }
      );
      
      if (!result.success) {
        throw result.error || new Error('Failed to publish message after retries');
      }
      
      this.logger.info('Message published successfully', {
        exchange: this.exchange.name,
        routingKey,
        messageId: publishOpts.messageId,
        documentType: payload.documentType,
      });
      
      return true;
      
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      
      // Add context to the error
      (err as any).type = RetryableErrorType.QUEUE;
      (err as any).context = {
        exchange: this.exchange.name,
        routingKey,
        messageId: payload.id,
      };
      
      logError(this.logger, 'Failed to publish message to RabbitMQ', err, {
        exchange: this.exchange.name,
        routingKey,
        messageId: payload.id,
        documentType: payload.documentType,
      });
      
      throw err;
    }
  }
  
  /**
   * Publishes a document message to the MCA documents exchange
   * 
   * @param payload - The document message payload
   * @returns A promise that resolves when the message is published
   */
  public async publishDocumentMessage(payload: IMessagePayload): Promise<boolean> {
    return this.publishMessage(payload);
  }
  
  /**
   * Checks if the service is connected to RabbitMQ
   * 
   * @returns True if connected, false otherwise
   */
  public isConnected(): boolean {
    return (
      this.connectionState === ConnectionState.CONNECTED &&
      this.connection !== null &&
      this.channel !== null
    );
  }
  
  /**
   * Closes the RabbitMQ connection and channel
   * 
   * @returns A promise that resolves when the connection is closed
   */
  public async close(): Promise<void> {
    this.logger.info('Closing RabbitMQ connection');
    
    // Clear any reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    this.connectionState = ConnectionState.CLOSING;
    
    try {
      // Close channel if it exists
      if (this.channel) {
        this.logger.debug('Closing RabbitMQ channel');
        await this.channel.close();
        this.channel = null;
      }
      
      // Close connection if it exists
      if (this.connection) {
        this.logger.debug('Closing RabbitMQ connection');
        await this.connection.close();
        this.connection = null;
      }
      
      this.connectionState = ConnectionState.CLOSED;
      this.logger.info('RabbitMQ connection closed successfully');
      
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      logError(this.logger, 'Error closing RabbitMQ connection', err);
      
      // Reset connection and channel
      this.connection = null;
      this.channel = null;
      this.connectionState = ConnectionState.CLOSED;
      
      throw err;
    }
  }
}

/**
 * Singleton instance of the MessageQueueService
 */
export const messageQueueService = new MessageQueueService();

/**
 * Default export for the MessageQueueService singleton
 */
export default messageQueueService;