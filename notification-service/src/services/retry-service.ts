/**
 * Retry Service
 * 
 * This service manages the retry mechanism for failed notification deliveries.
 * It implements an exponential backoff algorithm, maintains a retry queue, and
 * handles permanent failures after exhausting retry attempts.
 * 
 * Key features:
 * - Exponential backoff algorithm for retry scheduling
 * - Retry queue management with prioritization
 * - Retry attempt tracking and limit enforcement
 * - Dead letter queue for persistently failed notifications
 * - Retry status reporting and monitoring
 * - Configurable retry parameters (counts, intervals, backoff factor)
 */

import { EventEmitter } from 'events';
import { Logger } from 'winston';
import { IWebhookDeliveryResult, IWebhookPayload, IWebhookRetryPolicy } from '../types/webhook';
import { NotificationStatus } from '../types/notification';
import { deadLetterQueueConfig, defaultRetryPolicy } from '../config/webhook';
import {
  RetryOptions,
  RetryState,
  calculateNextRetryTime,
  createRetryState,
  formatRetryForLogging,
  isRetryExhausted,
  prepareForNextRetry,
  shouldRetry
} from '../utils/retry';

/**
 * Interface for a notification that needs to be retried
 */
export interface RetryItem {
  /** Unique identifier for the retry item */
  id: string;
  /** The webhook payload to deliver */
  payload: IWebhookPayload;
  /** The current retry state */
  retryState: RetryState;
  /** The webhook ID this notification is for */
  webhookId: string;
  /** The original error that caused the retry */
  error: Error;
  /** Timestamp when the item was added to the retry queue */
  queuedAt: number;
  /** Priority of the retry (higher values are processed first) */
  priority: number;
  /** Additional metadata for the retry item */
  metadata?: Record<string, any>;
}

/**
 * Interface for retry queue statistics
 */
export interface RetryQueueStats {
  /** Total number of items in the retry queue */
  totalItems: number;
  /** Number of items ready to be retried */
  readyItems: number;
  /** Number of items waiting for their next retry time */
  waitingItems: number;
  /** Number of items sent to the dead letter queue */
  deadLetterItems: number;
  /** Average retry attempts across all items */
  averageAttempts: number;
  /** Distribution of items by retry attempt */
  attemptDistribution: Record<number, number>;
  /** Oldest item in the queue (timestamp) */
  oldestItemTimestamp: number | null;
  /** Newest item in the queue (timestamp) */
  newestItemTimestamp: number | null;
}

/**
 * Events emitted by the RetryService
 */
export enum RetryServiceEvent {
  /** Emitted when an item is added to the retry queue */
  ITEM_QUEUED = 'item_queued',
  /** Emitted when an item is ready to be retried */
  ITEM_READY = 'item_ready',
  /** Emitted when an item is successfully retried */
  RETRY_SUCCESS = 'retry_success',
  /** Emitted when an item fails to be retried */
  RETRY_FAILURE = 'retry_failure',
  /** Emitted when an item is sent to the dead letter queue */
  DEAD_LETTER = 'dead_letter',
  /** Emitted when the retry queue is processed */
  QUEUE_PROCESSED = 'queue_processed',
  /** Emitted when an error occurs in the retry service */
  ERROR = 'error'
}

/**
 * Service that manages the retry mechanism for failed notification deliveries.
 */
export class RetryService extends EventEmitter {
  private retryQueue: Map<string, RetryItem> = new Map();
  private deadLetterQueue: Map<string, RetryItem> = new Map();
  private processingInterval: NodeJS.Timeout | null = null;
  private logger: Logger;
  private retryPolicy: IWebhookRetryPolicy;
  private isProcessing: boolean = false;
  private metrics: {
    totalQueued: number;
    totalRetried: number;
    totalSucceeded: number;
    totalFailed: number;
    totalDeadLettered: number;
  } = {
    totalQueued: 0,
    totalRetried: 0,
    totalSucceeded: 0,
    totalFailed: 0,
    totalDeadLettered: 0
  };

  /**
   * Creates a new RetryService instance
   * 
   * @param logger Winston logger instance
   * @param retryPolicy Retry policy configuration (optional, uses default if not provided)
   */
  constructor(logger: Logger, retryPolicy: IWebhookRetryPolicy = defaultRetryPolicy) {
    super();
    this.logger = logger;
    this.retryPolicy = retryPolicy;
  }

  /**
   * Starts the retry service
   * 
   * @param processingIntervalMs Interval in milliseconds to process the retry queue (default: 5000)
   */
  public start(processingIntervalMs: number = 5000): void {
    if (this.processingInterval) {
      this.stop();
    }

    this.logger.info('Starting retry service', {
      processingIntervalMs,
      retryPolicy: this.retryPolicy
    });

    this.processingInterval = setInterval(() => {
      this.processRetryQueue().catch(error => {
        this.logger.error('Error processing retry queue', { error });
        this.emit(RetryServiceEvent.ERROR, error);
      });
    }, processingIntervalMs);
  }

  /**
   * Stops the retry service
   */
  public stop(): void {
    if (this.processingInterval) {
      clearInterval(this.processingInterval);
      this.processingInterval = null;
      this.logger.info('Retry service stopped');
    }
  }

  /**
   * Queues a failed notification for retry
   * 
   * @param payload The webhook payload to retry
   * @param webhookId The ID of the webhook endpoint
   * @param error The error that caused the failure
   * @param priority Priority of the retry (higher values are processed first)
   * @param metadata Additional metadata for the retry item
   * @returns The created retry item
   */
  public queueForRetry(
    payload: IWebhookPayload,
    webhookId: string,
    error: Error,
    priority: number = 0,
    metadata?: Record<string, any>
  ): RetryItem {
    // Create a unique ID for the retry item
    const id = `${payload.id}-${Date.now()}`;

    // Create the initial retry state
    const retryState = createRetryState(error);

    // Prepare for the first retry
    const updatedRetryState = prepareForNextRetry(
      retryState,
      error,
      this.convertRetryPolicy(this.retryPolicy)
    );

    // Create the retry item
    const retryItem: RetryItem = {
      id,
      payload,
      retryState: updatedRetryState,
      webhookId,
      error,
      queuedAt: Date.now(),
      priority,
      metadata
    };

    // Add to the retry queue
    this.retryQueue.set(id, retryItem);
    this.metrics.totalQueued++;

    this.logger.info('Notification queued for retry', {
      id,
      webhookId,
      eventType: payload.eventType,
      nextRetryTime: updatedRetryState.nextRetryTime
        ? new Date(updatedRetryState.nextRetryTime).toISOString()
        : null,
      error: error.message
    });

    // Emit the queued event
    this.emit(RetryServiceEvent.ITEM_QUEUED, retryItem);

    return retryItem;
  }

  /**
   * Processes the retry queue, attempting to deliver notifications that are ready for retry
   */
  public async processRetryQueue(): Promise<void> {
    if (this.isProcessing) {
      this.logger.debug('Retry queue is already being processed');
      return;
    }

    this.isProcessing = true;

    try {
      const now = Date.now();
      const readyItems: RetryItem[] = [];

      // Find items that are ready to be retried
      for (const item of this.retryQueue.values()) {
        if (item.retryState.nextRetryTime && item.retryState.nextRetryTime <= now) {
          readyItems.push(item);
        }
      }

      // Sort by priority (higher first) and then by age (older first)
      readyItems.sort((a, b) => {
        if (a.priority !== b.priority) {
          return b.priority - a.priority; // Higher priority first
        }
        return a.queuedAt - b.queuedAt; // Older items first
      });

      this.logger.debug('Processing retry queue', {
        totalItems: this.retryQueue.size,
        readyItems: readyItems.length
      });

      // Process each ready item
      for (const item of readyItems) {
        this.emit(RetryServiceEvent.ITEM_READY, item);
        this.metrics.totalRetried++;

        // This is where we would actually attempt to deliver the notification
        // For now, we'll just simulate success or failure
        // In a real implementation, this would call the webhook service to attempt delivery
        try {
          // Simulate a delivery attempt
          // In a real implementation, this would be replaced with actual delivery logic
          const success = Math.random() > 0.5; // 50% chance of success for simulation

          if (success) {
            // Successful delivery
            this.handleRetrySuccess(item);
          } else {
            // Failed delivery
            throw new Error('Simulated delivery failure');
          }
        } catch (error) {
          // Handle retry failure
          this.handleRetryFailure(item, error instanceof Error ? error : new Error(String(error)));
        }
      }

      // Emit queue processed event with statistics
      this.emit(RetryServiceEvent.QUEUE_PROCESSED, this.getQueueStats());
    } finally {
      this.isProcessing = false;
    }
  }

  /**
   * Handles a successful retry attempt
   * 
   * @param item The retry item that was successfully delivered
   */
  private handleRetrySuccess(item: RetryItem): void {
    // Remove the item from the retry queue
    this.retryQueue.delete(item.id);
    this.metrics.totalSucceeded++;

    this.logger.info('Retry succeeded', {
      id: item.id,
      webhookId: item.webhookId,
      eventType: item.payload.eventType,
      attempts: item.retryState.attempt
    });

    // Create a delivery result for the successful retry
    const deliveryResult: IWebhookDeliveryResult = {
      id: `${item.id}-success`,
      webhookId: item.webhookId,
      eventId: item.payload.id,
      timestamp: new Date().toISOString(),
      success: true,
      statusCode: 200, // Simulated success status code
      deliveryTimeMs: 0, // Not tracking actual delivery time in this example
      retryCount: item.retryState.attempt
    };

    // Emit the success event
    this.emit(RetryServiceEvent.RETRY_SUCCESS, item, deliveryResult);
  }

  /**
   * Handles a failed retry attempt
   * 
   * @param item The retry item that failed to be delivered
   * @param error The error that caused the failure
   */
  private handleRetryFailure(item: RetryItem, error: Error): void {
    this.metrics.totalFailed++;

    // Check if we should retry based on the error
    if (!shouldRetry(error)) {
      this.logger.warn('Non-retryable error, sending to dead letter queue', {
        id: item.id,
        webhookId: item.webhookId,
        error: error.message
      });

      // Send to dead letter queue
      this.sendToDeadLetterQueue(item, error);
      return;
    }

    // Update the retry state
    const updatedRetryState = prepareForNextRetry(
      item.retryState,
      error,
      this.convertRetryPolicy(this.retryPolicy)
    );

    // Check if retry attempts have been exhausted
    if (updatedRetryState.exhausted) {
      this.logger.warn('Retry attempts exhausted, sending to dead letter queue', {
        id: item.id,
        webhookId: item.webhookId,
        attempts: updatedRetryState.attempt,
        error: error.message
      });

      // Send to dead letter queue
      this.sendToDeadLetterQueue(item, error);
      return;
    }

    // Update the retry item with the new state
    const updatedItem: RetryItem = {
      ...item,
      retryState: updatedRetryState,
      error
    };

    // Update the retry queue
    this.retryQueue.set(item.id, updatedItem);

    this.logger.info('Retry failed, scheduled for next attempt', {
      id: item.id,
      webhookId: item.webhookId,
      eventType: item.payload.eventType,
      attempts: updatedRetryState.attempt,
      nextRetryTime: updatedRetryState.nextRetryTime
        ? new Date(updatedRetryState.nextRetryTime).toISOString()
        : null,
      error: error.message
    });

    // Create a delivery result for the failed retry
    const deliveryResult: IWebhookDeliveryResult = {
      id: `${item.id}-failure-${updatedRetryState.attempt}`,
      webhookId: item.webhookId,
      eventId: item.payload.id,
      timestamp: new Date().toISOString(),
      success: false,
      statusCode: 500, // Simulated error status code
      errorMessage: error.message,
      deliveryTimeMs: 0, // Not tracking actual delivery time in this example
      retryCount: updatedRetryState.attempt - 1, // Current attempt - 1 since this is the failure count
      nextRetryAt: updatedRetryState.nextRetryTime
        ? new Date(updatedRetryState.nextRetryTime).toISOString()
        : undefined
    };

    // Emit the failure event
    this.emit(RetryServiceEvent.RETRY_FAILURE, updatedItem, deliveryResult);
  }

  /**
   * Sends a failed notification to the dead letter queue
   * 
   * @param item The retry item to send to the dead letter queue
   * @param finalError The final error that caused the item to be sent to the dead letter queue
   */
  private sendToDeadLetterQueue(item: RetryItem, finalError: Error): void {
    // Remove from the retry queue
    this.retryQueue.delete(item.id);

    // Add to the dead letter queue if enabled
    if (deadLetterQueueConfig.enabled) {
      // Update the item with the final error
      const deadLetterItem: RetryItem = {
        ...item,
        error: finalError,
        metadata: {
          ...item.metadata,
          finalErrorMessage: finalError.message,
          finalErrorType: finalError.constructor.name,
          finalErrorTime: Date.now(),
          sentToDeadLetterQueueAt: Date.now()
        }
      };

      // Add to the dead letter queue
      this.deadLetterQueue.set(item.id, deadLetterItem);
      this.metrics.totalDeadLettered++;

      this.logger.warn('Notification sent to dead letter queue', {
        id: item.id,
        webhookId: item.webhookId,
        eventType: item.payload.eventType,
        attempts: item.retryState.attempt,
        finalError: finalError.message
      });

      // In a real implementation, we would also publish to a dead letter exchange in RabbitMQ
      // for administrative review and potential manual reprocessing

      // Emit the dead letter event
      this.emit(RetryServiceEvent.DEAD_LETTER, deadLetterItem);
    } else {
      this.logger.warn('Dead letter queue disabled, discarding failed notification', {
        id: item.id,
        webhookId: item.webhookId,
        eventType: item.payload.eventType,
        attempts: item.retryState.attempt,
        finalError: finalError.message
      });
    }
  }

  /**
   * Gets statistics about the retry queue
   * 
   * @returns Statistics about the retry queue
   */
  public getQueueStats(): RetryQueueStats {
    const now = Date.now();
    let readyItems = 0;
    let waitingItems = 0;
    let totalAttempts = 0;
    let oldestTimestamp: number | null = null;
    let newestTimestamp: number | null = null;
    const attemptDistribution: Record<number, number> = {};

    // Calculate statistics
    for (const item of this.retryQueue.values()) {
      // Count ready vs waiting items
      if (item.retryState.nextRetryTime && item.retryState.nextRetryTime <= now) {
        readyItems++;
      } else {
        waitingItems++;
      }

      // Track attempt distribution
      const attempt = item.retryState.attempt;
      attemptDistribution[attempt] = (attemptDistribution[attempt] || 0) + 1;

      // Track total attempts for average calculation
      totalAttempts += attempt;

      // Track oldest and newest items
      if (oldestTimestamp === null || item.queuedAt < oldestTimestamp) {
        oldestTimestamp = item.queuedAt;
      }
      if (newestTimestamp === null || item.queuedAt > newestTimestamp) {
        newestTimestamp = item.queuedAt;
      }
    }

    return {
      totalItems: this.retryQueue.size,
      readyItems,
      waitingItems,
      deadLetterItems: this.deadLetterQueue.size,
      averageAttempts: this.retryQueue.size > 0 ? totalAttempts / this.retryQueue.size : 0,
      attemptDistribution,
      oldestItemTimestamp: oldestTimestamp,
      newestItemTimestamp: newestTimestamp
    };
  }

  /**
   * Gets metrics about the retry service
   * 
   * @returns Metrics about the retry service
   */
  public getMetrics(): typeof this.metrics {
    return { ...this.metrics };
  }

  /**
   * Gets all items in the retry queue
   * 
   * @returns Array of all retry items
   */
  public getAllRetryItems(): RetryItem[] {
    return Array.from(this.retryQueue.values());
  }

  /**
   * Gets all items in the dead letter queue
   * 
   * @returns Array of all dead letter items
   */
  public getAllDeadLetterItems(): RetryItem[] {
    return Array.from(this.deadLetterQueue.values());
  }

  /**
   * Gets a specific retry item by ID
   * 
   * @param id ID of the retry item to get
   * @returns The retry item, or undefined if not found
   */
  public getRetryItem(id: string): RetryItem | undefined {
    return this.retryQueue.get(id);
  }

  /**
   * Gets a specific dead letter item by ID
   * 
   * @param id ID of the dead letter item to get
   * @returns The dead letter item, or undefined if not found
   */
  public getDeadLetterItem(id: string): RetryItem | undefined {
    return this.deadLetterQueue.get(id);
  }

  /**
   * Removes a specific retry item from the queue
   * 
   * @param id ID of the retry item to remove
   * @returns True if the item was removed, false if it wasn't found
   */
  public removeRetryItem(id: string): boolean {
    return this.retryQueue.delete(id);
  }

  /**
   * Removes a specific dead letter item from the queue
   * 
   * @param id ID of the dead letter item to remove
   * @returns True if the item was removed, false if it wasn't found
   */
  public removeDeadLetterItem(id: string): boolean {
    return this.deadLetterQueue.delete(id);
  }

  /**
   * Clears all items from the retry queue
   */
  public clearRetryQueue(): void {
    this.retryQueue.clear();
    this.logger.info('Retry queue cleared');
  }

  /**
   * Clears all items from the dead letter queue
   */
  public clearDeadLetterQueue(): void {
    this.deadLetterQueue.clear();
    this.logger.info('Dead letter queue cleared');
  }

  /**
   * Requeues a dead letter item for retry
   * 
   * @param id ID of the dead letter item to requeue
   * @param resetAttempts Whether to reset the retry attempts (default: true)
   * @returns The requeued retry item, or undefined if the item wasn't found
   */
  public requeueDeadLetterItem(id: string, resetAttempts: boolean = true): RetryItem | undefined {
    const deadLetterItem = this.deadLetterQueue.get(id);
    if (!deadLetterItem) {
      return undefined;
    }

    // Remove from the dead letter queue
    this.deadLetterQueue.delete(id);

    // Create a new retry item with reset state if requested
    const retryItem: RetryItem = {
      ...deadLetterItem,
      retryState: resetAttempts ? createRetryState(deadLetterItem.error) : deadLetterItem.retryState,
      queuedAt: Date.now(),
      metadata: {
        ...deadLetterItem.metadata,
        requeuedAt: Date.now(),
        previouslyDeadLettered: true
      }
    };

    // Prepare for retry
    const updatedRetryState = prepareForNextRetry(
      retryItem.retryState,
      retryItem.error,
      this.convertRetryPolicy(this.retryPolicy)
    );

    // Update the retry state
    retryItem.retryState = updatedRetryState;

    // Add to the retry queue
    this.retryQueue.set(retryItem.id, retryItem);

    this.logger.info('Dead letter item requeued for retry', {
      id: retryItem.id,
      webhookId: retryItem.webhookId,
      eventType: retryItem.payload.eventType,
      resetAttempts,
      nextRetryTime: updatedRetryState.nextRetryTime
        ? new Date(updatedRetryState.nextRetryTime).toISOString()
        : null
    });

    // Emit the queued event
    this.emit(RetryServiceEvent.ITEM_QUEUED, retryItem);

    return retryItem;
  }

  /**
   * Updates the retry policy
   * 
   * @param retryPolicy New retry policy configuration
   */
  public updateRetryPolicy(retryPolicy: IWebhookRetryPolicy): void {
    this.retryPolicy = retryPolicy;
    this.logger.info('Retry policy updated', { retryPolicy });
  }

  /**
   * Converts an IWebhookRetryPolicy to RetryOptions
   * 
   * @param policy The webhook retry policy to convert
   * @returns Equivalent RetryOptions
   */
  private convertRetryPolicy(policy: IWebhookRetryPolicy): RetryOptions {
    return {
      baseDelayMs: policy.initialDelayMs,
      exponentialFactor: policy.backoffMultiplier,
      maxDelayMs: policy.maxDelayMs,
      maxRetries: policy.maxRetries,
      jitterFactor: policy.useJitter ? (policy.jitterFactor || 0.1) : 0
    };
  }
}

export default RetryService;