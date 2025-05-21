/**
 * Message Queue Service
 * 
 * This service manages the connection to RabbitMQ and handles publishing messages
 * about new documents to the message queue. It implements the IMessagePublisher
 * interface defined in the message-queue.ts types file.
 * 
 * Key features:
 * - RabbitMQ connection with TLS and client certificate authentication
 * - Publishing to the 'mca.documents' exchange (fanout)
 * - Message serialization for consistent JSON format
 * - Retry logic for failed message publishing
 * - Connection error handling and recovery strategies
 */

import amqplib, { Channel, Connection, Options } from 'amqplib';
import { Logger } from 'winston';

import {
  ConnectionEvent,
  ConnectionState,
  DEFAULT_MCA_EXCHANGE,
  DEFAULT_PUBLISH_OPTIONS,
  IExchangeConfig,
  IMessagePayload,
  IMessagePublisher,
  IPublishOptions,
  IRabbitMQConfig,
  IRetryConfig
} from '../types/message-queue';
import { IErrorDetails, IResult } from '../types/common';

/**
 * Default retry configuration for message publishing
 */
const DEFAULT_RETRY_CONFIG: IRetryConfig = {
  maxRetries: 5,
  initialDelay: 100, // ms
  maxDelay: 30000, // 30 seconds
  backoffFactor: 2,
  jitter: true
};

/**
 * Implementation of the IMessagePublisher interface for RabbitMQ
 */
export class MessageQueueService implements IMessagePublisher {
  private connection: Connection | null = null;
  private channel: Channel | null = null;
  private connectionState: ConnectionState = ConnectionState.DISCONNECTED;
  private eventListeners: Map<ConnectionEvent, Array<(data?: unknown) => void>> = new Map();
  private reconnectTimer: NodeJS.Timeout | null = null;
  private reconnectAttempts = 0;
  private readonly maxReconnectAttempts = 10;
  private readonly initialReconnectDelay = 1000; // 1 second
  private readonly maxReconnectDelay = 60000; // 1 minute

  /**
   * Creates a new MessageQueueService instance
   * 
   * @param config - RabbitMQ connection configuration
   * @param logger - Winston logger instance
   * @param retryConfig - Configuration for retry logic
   */
  constructor(
    private readonly config: IRabbitMQConfig,
    private readonly logger: Logger,
    private readonly retryConfig: IRetryConfig = DEFAULT_RETRY_CONFIG
  ) {
    // Initialize event listener maps
    Object.values(ConnectionEvent).forEach(event => {
      this.eventListeners.set(event, []);
    });
  }

  /**
   * Initializes the message queue service
   * Establishes connection to RabbitMQ and sets up the exchange
   */
  public async initialize(): Promise<IResult<void>> {
    try {
      this.logger.info('Initializing RabbitMQ connection');
      const connectionResult = await this.connect();
      
      if (!connectionResult.success) {
        return connectionResult;
      }

      // Assert the exchange exists
      await this.assertExchange(DEFAULT_MCA_EXCHANGE);
      
      this.logger.info(`RabbitMQ exchange '${DEFAULT_MCA_EXCHANGE.name}' initialized successfully`);
      return { success: true };
    } catch (error) {
      const errorDetails = this.createErrorDetails('RABBITMQ_INIT_ERROR', error);
      this.logger.error('Failed to initialize RabbitMQ connection', errorDetails);
      return { success: false, error: errorDetails };
    }
  }

  /**
   * Publishes a message to the specified exchange
   * 
   * @param exchange - Exchange name
   * @param routingKey - Routing key
   * @param payload - Message payload
   * @param options - Publishing options
   */
  public async publish(
    exchange: string,
    routingKey: string,
    payload: IMessagePayload,
    options: Partial<IPublishOptions> = {}
  ): Promise<IResult<void>> {
    // Combine default options with provided options
    const publishOptions: IPublishOptions = {
      ...DEFAULT_PUBLISH_OPTIONS,
      ...options,
      headers: {
        ...DEFAULT_PUBLISH_OPTIONS.headers,
        ...options.headers
      }
    };

    // Add timestamp if not provided
    if (!publishOptions.timestamp) {
      publishOptions.timestamp = Math.floor(Date.now() / 1000);
    }

    // Add message ID if not provided
    if (!publishOptions.messageId) {
      publishOptions.messageId = this.generateMessageId();
    }

    try {
      // Ensure we have a connection and channel
      if (!this.isConnected()) {
        const connectionResult = await this.connect();
        if (!connectionResult.success) {
          return connectionResult;
        }
      }

      // Serialize the payload to JSON
      const content = Buffer.from(JSON.stringify(payload));

      // Attempt to publish with retry logic
      return await this.publishWithRetry(exchange, routingKey, content, publishOptions);
    } catch (error) {
      const errorDetails = this.createErrorDetails('RABBITMQ_PUBLISH_ERROR', error);
      this.logger.error(`Failed to publish message to exchange '${exchange}'`, errorDetails);
      return { success: false, error: errorDetails };
    }
  }

  /**
   * Closes the RabbitMQ connection and releases resources
   */
  public async close(): Promise<IResult<void>> {
    try {
      this.logger.info('Closing RabbitMQ connection');
      
      // Clear any reconnect timer
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }

      // Close the channel if it exists
      if (this.channel) {
        await this.channel.close();
        this.channel = null;
      }

      // Close the connection if it exists
      if (this.connection) {
        await this.connection.close();
        this.connection = null;
      }

      this.connectionState = ConnectionState.DISCONNECTED;
      this.emitEvent(ConnectionEvent.DISCONNECTED);
      
      this.logger.info('RabbitMQ connection closed successfully');
      return { success: true };
    } catch (error) {
      const errorDetails = this.createErrorDetails('RABBITMQ_CLOSE_ERROR', error);
      this.logger.error('Failed to close RabbitMQ connection', errorDetails);
      return { success: false, error: errorDetails };
    }
  }

  /**
   * Adds an event listener for connection events
   * 
   * @param event - Connection event to listen for
   * @param listener - Event listener function
   */
  public on(event: ConnectionEvent, listener: (data?: unknown) => void): void {
    const listeners = this.eventListeners.get(event) || [];
    listeners.push(listener);
    this.eventListeners.set(event, listeners);
  }

  /**
   * Removes an event listener
   * 
   * @param event - Connection event
   * @param listener - Event listener function to remove
   */
  public off(event: ConnectionEvent, listener: (data?: unknown) => void): void {
    const listeners = this.eventListeners.get(event) || [];
    const index = listeners.indexOf(listener);
    if (index !== -1) {
      listeners.splice(index, 1);
      this.eventListeners.set(event, listeners);
    }
  }

  /**
   * Checks if connected to RabbitMQ
   */
  public isConnected(): boolean {
    return (
      this.connectionState === ConnectionState.CONNECTED &&
      this.connection !== null &&
      this.channel !== null
    );
  }

  /**
   * Connects to RabbitMQ
   */
  private async connect(): Promise<IResult<void>> {
    // If already connected or connecting, return
    if (
      this.connectionState === ConnectionState.CONNECTED ||
      this.connectionState === ConnectionState.CONNECTING
    ) {
      return { success: true };
    }

    try {
      this.connectionState = ConnectionState.CONNECTING;
      this.logger.info('Connecting to RabbitMQ', { host: this.config.host, port: this.config.port });

      // Build connection options
      const connectionOptions: Options.Connect = {
        protocol: this.config.useTls ? 'amqps' : 'amqp',
        hostname: this.config.host,
        port: this.config.port,
        username: this.config.username,
        password: this.config.password,
        vhost: this.config.vhost,
        timeout: this.config.connectionTimeout,
        heartbeat: this.config.heartbeat
      };

      // Add TLS options if enabled
      if (this.config.useTls && this.config.tlsOptions) {
        connectionOptions.cert = this.config.tlsOptions.ca;
        connectionOptions.rejectUnauthorized = this.config.tlsOptions.rejectUnauthorized;
      }

      // Connect to RabbitMQ
      this.connection = await amqplib.connect(connectionOptions);

      // Set up connection event handlers
      this.connection.on('error', (err) => this.handleConnectionError(err));
      this.connection.on('close', () => this.handleConnectionClosed());
      
      // Create a channel
      this.channel = await this.connection.createChannel();
      
      // Set up channel event handlers
      this.channel.on('error', (err) => this.handleChannelError(err));
      this.channel.on('close', () => this.handleChannelClosed());
      
      // Reset reconnect attempts on successful connection
      this.reconnectAttempts = 0;
      this.connectionState = ConnectionState.CONNECTED;
      this.emitEvent(ConnectionEvent.CONNECTED);
      
      this.logger.info('Successfully connected to RabbitMQ');
      return { success: true };
    } catch (error) {
      this.connectionState = ConnectionState.ERROR;
      const errorDetails = this.createErrorDetails('RABBITMQ_CONNECTION_ERROR', error);
      this.logger.error('Failed to connect to RabbitMQ', errorDetails);
      
      // Schedule reconnect attempt
      this.scheduleReconnect();
      
      this.emitEvent(ConnectionEvent.ERROR, errorDetails);
      return { success: false, error: errorDetails };
    }
  }

  /**
   * Asserts that an exchange exists, creating it if it doesn't
   * 
   * @param exchangeConfig - Exchange configuration
   */
  private async assertExchange(exchangeConfig: IExchangeConfig): Promise<void> {
    if (!this.channel) {
      throw new Error('Cannot assert exchange: Channel not available');
    }

    await this.channel.assertExchange(
      exchangeConfig.name,
      exchangeConfig.type,
      {
        durable: exchangeConfig.durable,
        autoDelete: exchangeConfig.autoDelete,
        arguments: exchangeConfig.arguments
      }
    );
  }

  /**
   * Publishes a message with retry logic
   * 
   * @param exchange - Exchange name
   * @param routingKey - Routing key
   * @param content - Message content
   * @param options - Publishing options
   */
  private async publishWithRetry(
    exchange: string,
    routingKey: string,
    content: Buffer,
    options: IPublishOptions
  ): Promise<IResult<void>> {
    let attempt = 0;
    let lastError: IErrorDetails | undefined;

    while (attempt <= this.retryConfig.maxRetries) {
      try {
        if (!this.channel) {
          throw new Error('Channel not available');
        }

        // Publish the message
        const published = this.channel.publish(
          exchange,
          routingKey,
          content,
          options as Options.Publish
        );

        if (published) {
          // Log success on first attempt or after retries
          if (attempt === 0) {
            this.logger.debug(`Published message to exchange '${exchange}' with routing key '${routingKey}'`);
          } else {
            this.logger.info(`Successfully published message to exchange '${exchange}' after ${attempt} retries`);
          }
          return { success: true };
        } else {
          // Channel buffer is full, wait and retry
          this.logger.warn(`Channel buffer full, retrying publish to exchange '${exchange}' (attempt ${attempt + 1} of ${this.retryConfig.maxRetries + 1})`);
          await this.delay(this.calculateBackoff(attempt));
          attempt++;
        }
      } catch (error) {
        lastError = this.createErrorDetails('RABBITMQ_PUBLISH_RETRY_ERROR', error);
        
        // Check if we should retry based on the error
        if (this.shouldRetry(error) && attempt < this.retryConfig.maxRetries) {
          const backoffTime = this.calculateBackoff(attempt);
          this.logger.warn(
            `Failed to publish message to exchange '${exchange}', retrying in ${backoffTime}ms (attempt ${attempt + 1} of ${this.retryConfig.maxRetries})`,
            lastError
          );
          
          await this.delay(backoffTime);
          attempt++;
          
          // If the connection was lost, try to reconnect
          if (!this.isConnected()) {
            const reconnectResult = await this.connect();
            if (!reconnectResult.success) {
              return reconnectResult;
            }
          }
        } else {
          // Max retries reached or non-retriable error
          this.logger.error(
            `Failed to publish message to exchange '${exchange}' after ${attempt} retries`,
            lastError
          );
          return { success: false, error: lastError };
        }
      }
    }

    // This should only happen if we've exhausted all retries
    return {
      success: false,
      error: lastError || this.createErrorDetails('RABBITMQ_MAX_RETRIES_EXCEEDED', new Error('Max retries exceeded'))
    };
  }

  /**
   * Determines if an error is retriable
   * 
   * @param error - The error to check
   */
  private shouldRetry(error: unknown): boolean {
    // Connection errors should be retried
    if (error instanceof Error) {
      // These error messages indicate temporary issues that can be retried
      const retriableErrors = [
        'connection closed',
        'channel closed',
        'connection reset',
        'socket hang up',
        'operation timed out',
        'unexpected socket close',
        'Channel buffer full',
        'Connection refused',
        'ECONNREFUSED',
        'ETIMEDOUT',
        'ECONNRESET',
        'EHOSTUNREACH'
      ];

      return retriableErrors.some(msg => error.message.includes(msg));
    }
    
    return false;
  }

  /**
   * Calculates backoff time with exponential backoff and optional jitter
   * 
   * @param attempt - Current attempt number (0-based)
   */
  private calculateBackoff(attempt: number): number {
    // Calculate exponential backoff
    const exponentialDelay = this.retryConfig.initialDelay * Math.pow(this.retryConfig.backoffFactor, attempt);
    
    // Apply maximum delay cap
    const cappedDelay = Math.min(exponentialDelay, this.retryConfig.maxDelay);
    
    // Add jitter if configured (±20% of the delay)
    if (this.retryConfig.jitter) {
      const jitterRange = cappedDelay * 0.2;
      return cappedDelay - jitterRange + (Math.random() * jitterRange * 2);
    }
    
    return cappedDelay;
  }

  /**
   * Handles connection errors
   * 
   * @param error - Connection error
   */
  private handleConnectionError(error: Error): void {
    const errorDetails = this.createErrorDetails('RABBITMQ_CONNECTION_ERROR', error);
    this.logger.error('RabbitMQ connection error', errorDetails);
    
    this.connectionState = ConnectionState.ERROR;
    this.emitEvent(ConnectionEvent.ERROR, errorDetails);
    
    // Schedule reconnect
    this.scheduleReconnect();
  }

  /**
   * Handles connection closed events
   */
  private handleConnectionClosed(): void {
    // Only log if we were previously connected (to avoid duplicate logs during intentional disconnects)
    if (this.connectionState === ConnectionState.CONNECTED) {
      this.logger.warn('RabbitMQ connection closed unexpectedly');
      
      this.connectionState = ConnectionState.DISCONNECTED;
      this.connection = null;
      this.channel = null;
      
      this.emitEvent(ConnectionEvent.DISCONNECTED);
      
      // Schedule reconnect
      this.scheduleReconnect();
    }
  }

  /**
   * Handles channel errors
   * 
   * @param error - Channel error
   */
  private handleChannelError(error: Error): void {
    const errorDetails = this.createErrorDetails('RABBITMQ_CHANNEL_ERROR', error);
    this.logger.error('RabbitMQ channel error', errorDetails);
    
    // Most channel errors are not recoverable, so we'll close and reconnect
    this.recreateChannel().catch(err => {
      this.logger.error('Failed to recreate channel after error', this.createErrorDetails('RABBITMQ_CHANNEL_RECREATION_ERROR', err));
    });
  }

  /**
   * Handles channel closed events
   */
  private handleChannelClosed(): void {
    // Only log if we were previously connected
    if (this.connectionState === ConnectionState.CONNECTED) {
      this.logger.warn('RabbitMQ channel closed unexpectedly');
      
      // Try to recreate the channel
      this.recreateChannel().catch(err => {
        this.logger.error('Failed to recreate channel after closure', this.createErrorDetails('RABBITMQ_CHANNEL_RECREATION_ERROR', err));
      });
    }
  }

  /**
   * Recreates the channel if the connection is still active
   */
  private async recreateChannel(): Promise<void> {
    if (this.connection && this.connectionState === ConnectionState.CONNECTED) {
      try {
        // Close the existing channel if it exists
        if (this.channel) {
          try {
            await this.channel.close();
          } catch (err) {
            // Ignore errors when closing an already closed channel
            this.logger.debug('Error while closing channel, likely already closed', { error: err });
          }
        }
        
        // Create a new channel
        this.channel = await this.connection.createChannel();
        
        // Set up channel event handlers
        this.channel.on('error', (err) => this.handleChannelError(err));
        this.channel.on('close', () => this.handleChannelClosed());
        
        // Re-assert the exchange
        await this.assertExchange(DEFAULT_MCA_EXCHANGE);
        
        this.logger.info('Successfully recreated RabbitMQ channel');
      } catch (error) {
        // If we can't recreate the channel, the connection might be bad
        // Schedule a full reconnect
        this.logger.error(
          'Failed to recreate channel, scheduling full reconnect',
          this.createErrorDetails('RABBITMQ_CHANNEL_RECREATION_FAILED', error)
        );
        
        this.connectionState = ConnectionState.ERROR;
        this.scheduleReconnect();
      }
    }
  }

  /**
   * Schedules a reconnection attempt with exponential backoff
   */
  private scheduleReconnect(): void {
    // Clear any existing reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    // Check if we've exceeded the maximum reconnect attempts
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.logger.error(
        `Failed to reconnect to RabbitMQ after ${this.maxReconnectAttempts} attempts, giving up`
      );
      return;
    }

    // Calculate backoff time
    const delay = Math.min(
      this.initialReconnectDelay * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectDelay
    );

    this.logger.info(`Scheduling RabbitMQ reconnect attempt in ${delay}ms (attempt ${this.reconnectAttempts + 1} of ${this.maxReconnectAttempts})`);

    // Schedule reconnect
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.reconnectAttempts++;
      
      // Attempt to reconnect
      this.connect().catch(err => {
        this.logger.error(
          'Error during scheduled reconnect',
          this.createErrorDetails('RABBITMQ_SCHEDULED_RECONNECT_ERROR', err)
        );
      });
    }, delay);
  }

  /**
   * Creates a promise that resolves after the specified delay
   * 
   * @param ms - Delay in milliseconds
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Generates a unique message ID
   */
  private generateMessageId(): string {
    return `${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;
  }

  /**
   * Creates standardized error details
   * 
   * @param code - Error code
   * @param error - Original error
   */
  private createErrorDetails(code: string, error: unknown): IErrorDetails {
    const message = error instanceof Error ? error.message : String(error);
    const stack = error instanceof Error ? error.stack : undefined;
    
    return {
      code,
      message,
      stack,
      timestamp: Date.now(),
      context: {
        host: this.config.host,
        port: this.config.port,
        connectionState: this.connectionState
      }
    };
  }

  /**
   * Emits an event to all registered listeners
   * 
   * @param event - Event to emit
   * @param data - Optional event data
   */
  private emitEvent(event: ConnectionEvent, data?: unknown): void {
    const listeners = this.eventListeners.get(event) || [];
    listeners.forEach(listener => {
      try {
        listener(data);
      } catch (error) {
        this.logger.error(
          `Error in RabbitMQ ${event} event listener`,
          this.createErrorDetails('RABBITMQ_EVENT_LISTENER_ERROR', error)
        );
      }
    });
  }
}