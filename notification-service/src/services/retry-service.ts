/**
 * Retry Service
 * 
 * This service manages the retry mechanism for failed notification deliveries.
 * It implements an exponential backoff algorithm, maintains a retry queue,
 * and handles permanent failures after exhausting retry attempts.
 * 
 * The service ensures reliable notification delivery even in the face of
 * temporary recipient unavailability by implementing sophisticated retry logic
 * with configurable parameters as specified in section 3.8.5.
 */

import { EventEmitter } from 'events';
import { Logger } from 'winston';
import * as retryUtils from '../utils/retry';
import type { IRetryConfig } from '../types/config';
import type { INotification, NotificationStatus } from '../types/notification';
import type { IWebhookDeliveryResult } from '../types/webhook';
import type { IRetryOptions } from '../types/common';

/**
 * Interface for retry queue items
 */
export interface RetryQueueItem {
  /** Unique identifier for the retry item */
  id: string;
  /** The notification to retry */
  notification: INotification;
  /** The webhook delivery result from the failed attempt */
  deliveryResult?: IWebhookDeliveryResult;
  /** Retry state tracking attempts and scheduling */
  retryState: retryUtils.RetryState;
  /** Priority of the retry (higher numbers = higher priority) */
  priority: number;
  /** Timestamp when the item was added to the retry queue */
  queuedAt: number;
  /** Timestamp when the item should be processed */
  scheduledAt: number;
  /** Whether the item is currently being processed */
  processing: boolean;
  /** Additional metadata for the retry */
  metadata?: Record<string, any>;
}

/**
 * Interface for dead letter queue items
 */
export interface DeadLetterQueueItem extends RetryQueueItem {
  /** Reason the item was moved to the dead letter queue */
  reason: string;
  /** Timestamp when the item was moved to the dead letter queue */
  deadLetteredAt: number;
  /** Final error that caused the item to be dead-lettered */
  finalError?: Error;
}

/**
 * Interface for retry statistics
 */
export interface RetryStats {
  /** Total number of items in the retry queue */
  queueSize: number;
  /** Total number of items in the dead letter queue */
  deadLetterSize: number;
  /** Number of items currently being processed */
  processingCount: number;
  /** Number of successful retries */
  successCount: number;
  /** Number of failed retries */
  failureCount: number;
  /** Number of items moved to the dead letter queue */
  deadLetterCount: number;
  /** Average retry attempts before success */
  avgAttemptsBeforeSuccess: number;
  /** Distribution of retry attempts */
  attemptDistribution: Record<number, number>;
  /** Distribution of error types */
  errorTypeDistribution: Record<string, number>;
  /** Timestamp when the stats were generated */
  timestamp: number;
}

/**
 * Events emitted by the RetryService
 */
export enum RetryServiceEvent {
  /** Emitted when an item is added to the retry queue */
  ITEM_QUEUED = 'item_queued',
  /** Emitted when a retry is attempted */
  RETRY_ATTEMPTED = 'retry_attempted',
  /** Emitted when a retry succeeds */
  RETRY_SUCCEEDED = 'retry_succeeded',
  /** Emitted when a retry fails */
  RETRY_FAILED = 'retry_failed',
  /** Emitted when an item is moved to the dead letter queue */
  DEAD_LETTERED = 'dead_lettered',
  /** Emitted when the retry service encounters an error */
  ERROR = 'error',
}

/**
 * Service that manages the retry mechanism for failed notification deliveries.
 * 
 * This service implements an exponential backoff algorithm, maintains a retry queue,
 * and handles permanent failures after exhausting retry attempts. It ensures reliable
 * notification delivery even in the face of temporary recipient unavailability.
 */
export class RetryService extends EventEmitter {
  private retryQueue: Map<string, RetryQueueItem>;
  private deadLetterQueue: Map<string, DeadLetterQueueItem>;
  private processingItems: Set<string>;
  private retryConfig: IRetryConfig;
  private logger: Logger;
  private scheduler: NodeJS.Timeout | null;
  private stats: RetryStats;
  private isProcessing: boolean;
  private webhookService: any; // Will be set via setWebhookService

  /**
   * Creates a new instance of the RetryService
   * 
   * @param retryConfig Configuration for the retry mechanism
   * @param logger Logger instance for logging retry operations
   */
  constructor(retryConfig: IRetryConfig, logger: Logger) {
    super();
    this.retryQueue = new Map<string, RetryQueueItem>();
    this.deadLetterQueue = new Map<string, DeadLetterQueueItem>();
    this.processingItems = new Set<string>();
    this.retryConfig = retryConfig;
    this.logger = logger;
    this.scheduler = null;
    this.isProcessing = false;
    this.webhookService = null;
    
    // Initialize statistics
    this.stats = {
      queueSize: 0,
      deadLetterSize: 0,
      processingCount: 0,
      successCount: 0,
      failureCount: 0,
      deadLetterCount: 0,
      avgAttemptsBeforeSuccess: 0,
      attemptDistribution: {},
      errorTypeDistribution: {},
      timestamp: Date.now(),
    };
  }

  /**
   * Sets the webhook service to use for retry attempts
   * This is set separately to avoid circular dependencies
   * 
   * @param webhookService The webhook service instance
   */
  public setWebhookService(webhookService: any): void {
    this.webhookService = webhookService;
  }

  /**
   * Starts the retry service
   */
  public start(): void {
    if (this.scheduler) {
      return; // Already started
    }

    this.logger.info('Starting retry service');
    
    // Start the scheduler to process the retry queue
    // Check every second for items that need to be retried
    this.scheduler = setInterval(() => this.processRetryQueue(), 1000);
  }

  /**
   * Stops the retry service
   */
  public stop(): void {
    if (!this.scheduler) {
      return; // Already stopped
    }

    this.logger.info('Stopping retry service');
    
    clearInterval(this.scheduler);
    this.scheduler = null;
  }

  /**
   * Adds a failed notification to the retry queue
   * 
   * @param notification The notification that failed to deliver
   * @param deliveryResult The result of the failed delivery attempt
   * @param error The error that occurred during delivery
   * @param options Optional retry options to override defaults
   * @returns The created retry queue item
   */
  public addToRetryQueue(
    notification: INotification,
    deliveryResult?: IWebhookDeliveryResult,
    error?: Error,
    options?: Partial<IRetryOptions>
  ): RetryQueueItem {
    if (!this.retryConfig.enabled) {
      throw new Error('Retry mechanism is disabled');
    }

    // Create retry options by merging defaults with provided options
    const retryOptions: retryUtils.RetryOptions = {
      baseDelayMs: options?.initialDelayMs ?? this.retryConfig.initialDelay,
      exponentialFactor: options?.backoffFactor ?? this.retryConfig.backoffMultiplier,
      maxDelayMs: options?.maxDelayMs ?? this.retryConfig.maxDelay,
      maxRetries: options?.maxRetries ?? this.retryConfig.maxAttempts,
      jitterFactor: this.retryConfig.enableJitter ? 0.2 : 0, // 20% jitter if enabled
    };

    // Create initial retry state
    const retryState = retryUtils.createRetryState(error);
    
    // Prepare for the first retry
    const preparedState = error 
      ? retryUtils.prepareForNextRetry(retryState, error, retryOptions)
      : retryState;
    
    // Determine priority based on notification priority
    // Higher numbers = higher priority
    let priority = 1; // Default priority
    
    if (notification.deliveryOptions?.priority) {
      switch (notification.deliveryOptions.priority) {
        case 'critical':
          priority = 4;
          break;
        case 'high':
          priority = 3;
          break;
        case 'medium':
          priority = 2;
          break;
        case 'low':
        default:
          priority = 1;
          break;
      }
    }

    // Create the retry queue item
    const queueItem: RetryQueueItem = {
      id: notification.id,
      notification,
      deliveryResult,
      retryState: preparedState,
      priority,
      queuedAt: Date.now(),
      scheduledAt: preparedState.nextRetryTime || Date.now(),
      processing: false,
      metadata: {
        retryOptions,
        originalError: error?.message,
        errorType: error?.constructor.name,
      },
    };

    // Add to the retry queue
    this.retryQueue.set(notification.id, queueItem);
    
    // Update notification status to RETRYING
    notification.status = NotificationStatus.RETRYING;
    notification.retryCount = preparedState.attempt;
    notification.nextRetryAt = preparedState.nextRetryTime;
    
    // Update statistics
    this.updateStats();
    
    // Log and emit event
    this.logger.info(
      `Added notification ${notification.id} to retry queue. Attempt: ${preparedState.attempt}, Next retry: ${new Date(preparedState.nextRetryTime || 0).toISOString()}`,
      { notificationId: notification.id, retryState: retryUtils.formatRetryForLogging(preparedState) }
    );
    
    this.emit(RetryServiceEvent.ITEM_QUEUED, queueItem);
    
    return queueItem;
  }

  /**
   * Processes the retry queue, attempting to deliver notifications that are due for retry
   */
  private async processRetryQueue(): Promise<void> {
    if (this.isProcessing || this.retryQueue.size === 0) {
      return; // Already processing or queue is empty
    }

    this.isProcessing = true;

    try {
      // Get all items that are due for retry, sorted by priority (highest first)
      const now = Date.now();
      const dueItems = Array.from(this.retryQueue.values())
        .filter(item => !item.processing && item.scheduledAt <= now)
        .sort((a, b) => b.priority - a.priority);

      if (dueItems.length === 0) {
        this.isProcessing = false;
        return; // No items due for retry
      }

      this.logger.debug(`Processing ${dueItems.length} items from retry queue`);

      // Process each due item
      const processPromises = dueItems.map(item => this.processRetryItem(item));
      
      // Wait for all items to be processed
      await Promise.all(processPromises);
    } catch (error) {
      this.logger.error('Error processing retry queue', { error });
      this.emit(RetryServiceEvent.ERROR, error);
    } finally {
      this.isProcessing = false;
      this.updateStats();
    }
  }

  /**
   * Processes a single retry queue item
   * 
   * @param item The retry queue item to process
   */
  private async processRetryItem(item: RetryQueueItem): Promise<void> {
    if (!this.webhookService) {
      this.logger.error('Cannot process retry item: webhook service not set');
      return;
    }

    // Mark as processing
    item.processing = true;
    this.processingItems.add(item.id);

    try {
      this.logger.info(
        `Attempting retry for notification ${item.id}. Attempt: ${item.retryState.attempt}`,
        { notificationId: item.id, retryAttempt: item.retryState.attempt }
      );

      this.emit(RetryServiceEvent.RETRY_ATTEMPTED, item);

      // Attempt to deliver the notification using the webhook service
      const result = await this.webhookService.deliverWebhook(item.notification);

      // If we get here, the delivery was successful
      this.handleRetrySuccess(item, result);
    } catch (error: any) {
      // Delivery failed, handle the failure
      this.handleRetryFailure(item, error);
    } finally {
      // Remove from processing set
      item.processing = false;
      this.processingItems.delete(item.id);
    }
  }

  /**
   * Handles a successful retry attempt
   * 
   * @param item The retry queue item that succeeded
   * @param result The result of the successful delivery
   */
  private handleRetrySuccess(item: RetryQueueItem, result: any): void {
    // Remove from retry queue
    this.retryQueue.delete(item.id);

    // Update notification status
    item.notification.status = NotificationStatus.DELIVERED;
    item.notification.deliveredAt = Date.now();
    item.notification.retryCount = item.retryState.attempt;
    item.notification.nextRetryAt = undefined;

    // Update statistics
    this.stats.successCount++;
    
    // Update attempt distribution
    const attempt = item.retryState.attempt;
    this.stats.attemptDistribution[attempt] = (this.stats.attemptDistribution[attempt] || 0) + 1;
    
    // Update average attempts before success
    const totalSuccessfulAttempts = Object.entries(this.stats.attemptDistribution)
      .reduce((sum, [attempt, count]) => sum + (parseInt(attempt) * count), 0);
    
    this.stats.avgAttemptsBeforeSuccess = totalSuccessfulAttempts / this.stats.successCount;

    // Log and emit event
    this.logger.info(
      `Successfully delivered notification ${item.id} after ${item.retryState.attempt} retry attempts`,
      { notificationId: item.id, retryAttempt: item.retryState.attempt, result }
    );

    this.emit(RetryServiceEvent.RETRY_SUCCEEDED, { item, result });
  }

  /**
   * Handles a failed retry attempt
   * 
   * @param item The retry queue item that failed
   * @param error The error that occurred during the retry attempt
   */
  private handleRetryFailure(item: RetryQueueItem, error: Error): void {
    // Create retry options
    const retryOptions: retryUtils.RetryOptions = item.metadata?.retryOptions || {
      baseDelayMs: this.retryConfig.initialDelay,
      exponentialFactor: this.retryConfig.backoffMultiplier,
      maxDelayMs: this.retryConfig.maxDelay,
      maxRetries: this.retryConfig.maxAttempts,
      jitterFactor: this.retryConfig.enableJitter ? 0.2 : 0,
    };

    // Update retry state
    const updatedState = retryUtils.prepareForNextRetry(item.retryState, error, retryOptions);
    item.retryState = updatedState;

    // Update error type distribution
    const errorType = error.constructor.name;
    this.stats.errorTypeDistribution[errorType] = (this.stats.errorTypeDistribution[errorType] || 0) + 1;

    // Check if retry limit has been reached
    if (updatedState.exhausted) {
      this.moveToDeadLetterQueue(item, error);
      return;
    }

    // Update item for next retry
    item.scheduledAt = updatedState.nextRetryTime || Date.now();
    
    // Update notification
    item.notification.status = NotificationStatus.RETRYING;
    item.notification.retryCount = updatedState.attempt;
    item.notification.nextRetryAt = updatedState.nextRetryTime;
    item.notification.failedAt = Date.now();
    item.notification.errorDetails = error.message;

    // Update statistics
    this.stats.failureCount++;

    // Log and emit event
    this.logger.warn(
      `Failed to deliver notification ${item.id}. Retry attempt: ${updatedState.attempt}. Next retry: ${new Date(updatedState.nextRetryTime || 0).toISOString()}`,
      { 
        notificationId: item.id, 
        retryAttempt: updatedState.attempt, 
        error: error.message,
        nextRetry: updatedState.nextRetryTime ? new Date(updatedState.nextRetryTime).toISOString() : null
      }
    );

    this.emit(RetryServiceEvent.RETRY_FAILED, { item, error });
  }

  /**
   * Moves a retry queue item to the dead letter queue after exhausting retry attempts
   * 
   * @param item The retry queue item to move to the dead letter queue
   * @param error The final error that caused the item to be dead-lettered
   */
  private moveToDeadLetterQueue(item: RetryQueueItem, error: Error): void {
    // Remove from retry queue
    this.retryQueue.delete(item.id);

    // Create dead letter queue item
    const deadLetterItem: DeadLetterQueueItem = {
      ...item,
      reason: `Retry limit exceeded after ${item.retryState.attempt} attempts`,
      deadLetteredAt: Date.now(),
      finalError: error,
    };

    // Add to dead letter queue
    this.deadLetterQueue.set(item.id, deadLetterItem);

    // Update notification status
    item.notification.status = NotificationStatus.FAILED;
    item.notification.failedAt = Date.now();
    item.notification.errorDetails = `${error.message} (Retry limit exceeded after ${item.retryState.attempt} attempts)`;
    item.notification.nextRetryAt = undefined;

    // Update statistics
    this.stats.deadLetterCount++;

    // Log and emit event
    this.logger.error(
      `Moving notification ${item.id} to dead letter queue after ${item.retryState.attempt} failed retry attempts`,
      { 
        notificationId: item.id, 
        retryAttempt: item.retryState.attempt, 
        error: error.message,
        retryHistory: item.retryState.retryHistory.map(time => new Date(time).toISOString())
      }
    );

    this.emit(RetryServiceEvent.DEAD_LETTERED, deadLetterItem);
  }

  /**
   * Gets an item from the retry queue by ID
   * 
   * @param id The ID of the retry queue item to get
   * @returns The retry queue item, or undefined if not found
   */
  public getRetryQueueItem(id: string): RetryQueueItem | undefined {
    return this.retryQueue.get(id);
  }

  /**
   * Gets an item from the dead letter queue by ID
   * 
   * @param id The ID of the dead letter queue item to get
   * @returns The dead letter queue item, or undefined if not found
   */
  public getDeadLetterQueueItem(id: string): DeadLetterQueueItem | undefined {
    return this.deadLetterQueue.get(id);
  }

  /**
   * Gets all items in the retry queue
   * 
   * @returns Array of all retry queue items
   */
  public getAllRetryQueueItems(): RetryQueueItem[] {
    return Array.from(this.retryQueue.values());
  }

  /**
   * Gets all items in the dead letter queue
   * 
   * @returns Array of all dead letter queue items
   */
  public getAllDeadLetterQueueItems(): DeadLetterQueueItem[] {
    return Array.from(this.deadLetterQueue.values());
  }

  /**
   * Removes an item from the retry queue
   * 
   * @param id The ID of the retry queue item to remove
   * @returns True if the item was removed, false if it wasn't found
   */
  public removeFromRetryQueue(id: string): boolean {
    const removed = this.retryQueue.delete(id);
    if (removed) {
      this.updateStats();
    }
    return removed;
  }

  /**
   * Removes an item from the dead letter queue
   * 
   * @param id The ID of the dead letter queue item to remove
   * @returns True if the item was removed, false if it wasn't found
   */
  public removeFromDeadLetterQueue(id: string): boolean {
    const removed = this.deadLetterQueue.delete(id);
    if (removed) {
      this.updateStats();
    }
    return removed;
  }

  /**
   * Requeues an item from the dead letter queue back to the retry queue
   * 
   * @param id The ID of the dead letter queue item to requeue
   * @param resetRetryCount Whether to reset the retry count (default: true)
   * @returns The requeued retry queue item, or undefined if the item wasn't found
   */
  public requeueFromDeadLetterQueue(id: string, resetRetryCount: boolean = true): RetryQueueItem | undefined {
    const deadLetterItem = this.deadLetterQueue.get(id);
    if (!deadLetterItem) {
      return undefined;
    }

    // Remove from dead letter queue
    this.deadLetterQueue.delete(id);

    // Create a new retry state if resetting retry count
    const retryState = resetRetryCount 
      ? retryUtils.createRetryState()
      : deadLetterItem.retryState;

    // Create retry options
    const retryOptions: retryUtils.RetryOptions = deadLetterItem.metadata?.retryOptions || {
      baseDelayMs: this.retryConfig.initialDelay,
      exponentialFactor: this.retryConfig.backoffMultiplier,
      maxDelayMs: this.retryConfig.maxDelay,
      maxRetries: this.retryConfig.maxAttempts,
      jitterFactor: this.retryConfig.enableJitter ? 0.2 : 0,
    };

    // Calculate next retry time
    const nextRetryTime = retryUtils.calculateNextRetryTime(
      resetRetryCount ? 0 : retryState.attempt,
      retryOptions
    );

    // Create retry queue item
    const queueItem: RetryQueueItem = {
      ...deadLetterItem,
      retryState: {
        ...retryState,
        nextRetryTime,
        exhausted: false,
      },
      scheduledAt: nextRetryTime,
      processing: false,
      queuedAt: Date.now(),
    };

    // Add to retry queue
    this.retryQueue.set(id, queueItem);

    // Update notification status
    queueItem.notification.status = NotificationStatus.RETRYING;
    queueItem.notification.retryCount = resetRetryCount ? 0 : retryState.attempt;
    queueItem.notification.nextRetryAt = nextRetryTime;

    // Update statistics
    this.updateStats();

    // Log requeue action
    this.logger.info(
      `Requeued notification ${id} from dead letter queue${resetRetryCount ? ' with reset retry count' : ''}`,
      { notificationId: id, resetRetryCount }
    );

    return queueItem;
  }

  /**
   * Gets current retry statistics
   * 
   * @returns Current retry statistics
   */
  public getStats(): RetryStats {
    this.updateStats();
    return { ...this.stats, timestamp: Date.now() };
  }

  /**
   * Updates the retry statistics
   */
  private updateStats(): void {
    this.stats.queueSize = this.retryQueue.size;
    this.stats.deadLetterSize = this.deadLetterQueue.size;
    this.stats.processingCount = this.processingItems.size;
  }

  /**
   * Clears all items from the retry and dead letter queues
   */
  public clearAllQueues(): void {
    this.retryQueue.clear();
    this.deadLetterQueue.clear();
    this.processingItems.clear();
    this.updateStats();
    this.logger.info('Cleared all retry and dead letter queues');
  }

  /**
   * Gets the current retry configuration
   * 
   * @returns Current retry configuration
   */
  public getRetryConfig(): IRetryConfig {
    return { ...this.retryConfig };
  }

  /**
   * Updates the retry configuration
   * 
   * @param config New retry configuration (partial)
   * @returns Updated retry configuration
   */
  public updateRetryConfig(config: Partial<IRetryConfig>): IRetryConfig {
    this.retryConfig = { ...this.retryConfig, ...config };
    this.logger.info('Updated retry configuration', { config: this.retryConfig });
    return { ...this.retryConfig };
  }
}

export default RetryService;