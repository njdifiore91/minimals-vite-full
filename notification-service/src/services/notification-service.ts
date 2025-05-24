import { Channel, ConsumeMessage } from 'amqplib';
import { Logger } from 'winston';

import {
  INotification,
  NotificationType,
  INotificationRecipient,
  NotificationStatus,
  NotificationPriority,
} from '../types/notification';
import { IRabbitMQMessage } from '../types/rabbitmq';
import { WebhookService } from './webhook-service';
import { RetryService } from './retry-service';
import { AuditService } from './audit-service';
import { MessageService } from './message-service';
import { rabbitmqConfig } from '../config/rabbitmq';

/**
 * NotificationService
 * 
 * Core service that processes notification messages from RabbitMQ, determines notification types,
 * resolves recipients, and orchestrates the delivery process. It acts as the central coordinator
 * for the notification system, consuming messages from the notification queue and delegating to
 * specialized services for delivery.
 */
export class NotificationService {
  private channel: Channel | null = null;
  private consumerTag: string | null = null;
  private isProcessing = false;

  /**
   * Creates an instance of NotificationService.
   * 
   * @param logger - Winston logger instance for service-wide logging
   * @param webhookService - Service for webhook payload delivery
   * @param messageService - Service for email, SMS, and push notifications
   * @param retryService - Service for managing notification retries
   * @param auditService - Service for logging notification activities
   */
  constructor(
    private readonly logger: Logger,
    private readonly webhookService: WebhookService,
    private readonly messageService: MessageService,
    private readonly retryService: RetryService,
    private readonly auditService: AuditService,
  ) {}

  /**
   * Initializes the notification service and sets up the RabbitMQ consumer.
   * 
   * @param channel - RabbitMQ channel for consuming messages
   * @returns Promise that resolves when initialization is complete
   */
  public async initialize(channel: Channel): Promise<void> {
    this.logger.info('Initializing NotificationService');
    this.channel = channel;

    try {
      // Ensure the notification queue exists
      await this.channel.assertQueue(rabbitmqConfig.queues.notification, {
        durable: true,
      });

      this.logger.info(`NotificationService initialized successfully`);
    } catch (error) {
      this.logger.error('Failed to initialize NotificationService', { error });
      throw error;
    }
  }

  /**
   * Starts consuming messages from the notification queue.
   * 
   * @returns Promise that resolves when the consumer is started
   */
  public async startConsumer(): Promise<void> {
    if (!this.channel) {
      throw new Error('NotificationService not initialized');
    }

    try {
      const { consumerTag } = await this.channel.consume(
        rabbitmqConfig.queues.notification,
        this.handleMessage.bind(this),
        { noAck: false }
      );

      this.consumerTag = consumerTag;
      this.logger.info('NotificationService consumer started', { consumerTag });
    } catch (error) {
      this.logger.error('Failed to start NotificationService consumer', { error });
      throw error;
    }
  }

  /**
   * Stops consuming messages from the notification queue.
   * 
   * @returns Promise that resolves when the consumer is stopped
   */
  public async stopConsumer(): Promise<void> {
    if (!this.channel || !this.consumerTag) {
      return;
    }

    try {
      await this.channel.cancel(this.consumerTag);
      this.consumerTag = null;
      this.logger.info('NotificationService consumer stopped');
    } catch (error) {
      this.logger.error('Failed to stop NotificationService consumer', { error });
      throw error;
    }
  }

  /**
   * Handles incoming notification messages from RabbitMQ.
   * 
   * @param msg - RabbitMQ message containing notification data
   */
  private async handleMessage(msg: ConsumeMessage | null): Promise<void> {
    if (!msg || !this.channel) {
      return;
    }

    // Set processing flag to track active processing
    this.isProcessing = true;

    try {
      // Parse the message content
      const content = msg.content.toString();
      const message: IRabbitMQMessage = JSON.parse(content);

      this.logger.info('Processing notification message', {
        messageId: message.messageId,
        correlationId: message.correlationId,
      });

      // Validate the message structure
      if (!this.validateMessage(message)) {
        this.logger.warn('Invalid notification message structure', { messageId: message.messageId });
        // Acknowledge invalid messages to remove them from the queue
        this.channel.ack(msg);
        return;
      }

      // Process the notification
      await this.processNotification(message);

      // Acknowledge the message after successful processing
      this.channel.ack(msg);
      this.logger.info('Notification message processed successfully', { messageId: message.messageId });
    } catch (error) {
      this.logger.error('Error processing notification message', { error });

      // Negative acknowledge the message to requeue it for retry
      // Only requeue if it hasn't been redelivered too many times
      const redelivered = msg.fields.redelivered;
      const redeliveryCount = this.getRedeliveryCount(msg);

      if (redelivered && redeliveryCount > rabbitmqConfig.maxRedeliveries) {
        this.logger.warn('Message exceeded max redeliveries, not requeuing', {
          redeliveryCount,
          maxRedeliveries: rabbitmqConfig.maxRedeliveries,
        });
        // Acknowledge the message to remove it from the queue
        this.channel.ack(msg);

        // Send to dead letter queue for manual inspection
        await this.sendToDeadLetterQueue(msg);
      } else {
        // Requeue the message for retry
        this.channel.nack(msg, false, true);
      }
    } finally {
      this.isProcessing = false;
    }
  }

  /**
   * Validates the structure of a notification message.
   * 
   * @param message - RabbitMQ message to validate
   * @returns True if the message is valid, false otherwise
   */
  private validateMessage(message: IRabbitMQMessage): boolean {
    // Basic validation of required fields
    if (!message || !message.payload) {
      return false;
    }

    // Validate notification-specific fields
    const payload = message.payload;
    if (!payload.type || !payload.applicationId) {
      return false;
    }

    return true;
  }

  /**
   * Processes a notification message by determining type, resolving recipients,
   * and delivering through appropriate channels.
   * 
   * @param message - RabbitMQ message containing notification data
   */
  private async processNotification(message: IRabbitMQMessage): Promise<void> {
    const { payload, messageId, correlationId } = message;

    // Create notification object from message payload
    const notification: INotification = {
      id: messageId,
      correlationId,
      type: this.determineNotificationType(payload),
      status: NotificationStatus.PENDING,
      priority: this.determinePriority(payload),
      applicationId: payload.applicationId,
      payload: payload,
      metadata: payload.metadata || {},
      recipients: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    // Log notification creation
    this.logger.info('Created notification', {
      notificationId: notification.id,
      type: notification.type,
      applicationId: notification.applicationId,
    });

    // Resolve recipients based on notification type and application metadata
    notification.recipients = await this.resolveRecipients(notification);

    if (notification.recipients.length === 0) {
      this.logger.warn('No recipients found for notification', {
        notificationId: notification.id,
        type: notification.type,
      });
      
      // Record the notification with no recipients
      await this.auditService.recordNotificationAttempt(notification, [], 'NO_RECIPIENTS');
      return;
    }

    // Deliver notification to all recipients through appropriate channels
    const deliveryResults = await this.deliverNotification(notification);

    // Update notification status based on delivery results
    notification.status = this.determineOverallStatus(deliveryResults);
    notification.updatedAt = new Date();

    // Record the notification delivery attempt
    await this.auditService.recordNotificationAttempt(
      notification,
      deliveryResults,
      notification.status
    );

    // Schedule retries for failed deliveries if applicable
    if (notification.status === NotificationStatus.FAILED || notification.status === NotificationStatus.PARTIALLY_DELIVERED) {
      await this.scheduleRetries(notification, deliveryResults);
    }
  }

  /**
   * Determines the notification type based on the message payload.
   * 
   * @param payload - Notification payload from RabbitMQ message
   * @returns The determined notification type
   */
  private determineNotificationType(payload: any): NotificationType {
    // Check for explicit type in the payload
    if (payload.type) {
      const type = payload.type.toUpperCase();
      if (Object.values(NotificationType).includes(type as NotificationType)) {
        return type as NotificationType;
      }
    }

    // Infer type from payload content if not explicitly specified
    if (payload.error || payload.errorCode) {
      return NotificationType.ERROR;
    }

    if (payload.status === 'COMPLETED' || payload.status === 'APPROVED') {
      return NotificationType.COMPLETION;
    }

    // Default to status update
    return NotificationType.STATUS_UPDATE;
  }

  /**
   * Determines the notification priority based on the message payload.
   * 
   * @param payload - Notification payload from RabbitMQ message
   * @returns The determined notification priority
   */
  private determinePriority(payload: any): NotificationPriority {
    // Check for explicit priority in the payload
    if (payload.priority) {
      const priority = payload.priority.toUpperCase();
      if (Object.values(NotificationPriority).includes(priority as NotificationPriority)) {
        return priority as NotificationPriority;
      }
    }

    // Infer priority from notification type and content
    if (payload.type === NotificationType.ERROR) {
      return NotificationPriority.HIGH;
    }

    if (payload.type === NotificationType.COMPLETION) {
      return NotificationPriority.MEDIUM;
    }

    // Check for urgent flag
    if (payload.urgent === true) {
      return NotificationPriority.HIGH;
    }

    // Default priority
    return NotificationPriority.MEDIUM;
  }

  /**
   * Resolves the recipients for a notification based on type and application metadata.
   * 
   * @param notification - Notification object to resolve recipients for
   * @returns Promise resolving to an array of notification recipients
   */
  private async resolveRecipients(notification: INotification): Promise<INotificationRecipient[]> {
    const recipients: INotificationRecipient[] = [];
    const { applicationId, type, metadata } = notification;

    try {
      // Get application details to determine recipients
      // This could involve a database lookup or API call to the Data Service
      // For now, we'll use the metadata from the notification itself

      // Check for explicitly specified recipients in the notification metadata
      if (metadata.recipients && Array.isArray(metadata.recipients)) {
        recipients.push(...metadata.recipients);
      }

      // If no explicit recipients, resolve based on application configuration
      if (recipients.length === 0) {
        // This would typically involve looking up webhook configurations, email preferences, etc.
        // For demonstration, we'll add a default webhook recipient
        recipients.push({
          type: 'webhook',
          endpoint: `https://api.example.com/webhooks/${applicationId}`,
          apiKey: metadata.apiKey || 'default-key',
        });

        // Add email recipient if email is available
        if (metadata.email) {
          recipients.push({
            type: 'email',
            email: metadata.email,
            name: metadata.name || '',
          });
        }
      }

      // Log the resolved recipients
      this.logger.info('Resolved notification recipients', {
        notificationId: notification.id,
        recipientCount: recipients.length,
      });

      return recipients;
    } catch (error) {
      this.logger.error('Error resolving notification recipients', {
        notificationId: notification.id,
        error,
      });
      
      // Return empty array on error
      return [];
    }
  }

  /**
   * Delivers a notification to all recipients through appropriate channels.
   * 
   * @param notification - Notification object to deliver
   * @returns Promise resolving to an array of delivery results
   */
  private async deliverNotification(notification: INotification): Promise<any[]> {
    const deliveryResults = [];

    // Process each recipient in parallel
    const deliveryPromises = notification.recipients.map(async (recipient) => {
      try {
        let result;

        // Route to appropriate delivery service based on recipient type
        switch (recipient.type) {
          case 'webhook':
            result = await this.webhookService.deliverWebhook(notification, recipient);
            break;
          case 'email':
            result = await this.messageService.sendEmail(notification, recipient);
            break;
          case 'sms':
            result = await this.messageService.sendSms(notification, recipient);
            break;
          case 'push':
            result = await this.messageService.sendPushNotification(notification, recipient);
            break;
          default:
            throw new Error(`Unsupported recipient type: ${recipient.type}`);
        }

        return {
          recipient,
          success: true,
          result,
          timestamp: new Date(),
        };
      } catch (error) {
        this.logger.error('Error delivering notification', {
          notificationId: notification.id,
          recipientType: recipient.type,
          error,
        });

        return {
          recipient,
          success: false,
          error: error.message || 'Unknown error',
          timestamp: new Date(),
        };
      }
    });

    // Wait for all deliveries to complete
    const results = await Promise.all(deliveryPromises);
    deliveryResults.push(...results);

    return deliveryResults;
  }

  /**
   * Determines the overall notification status based on delivery results.
   * 
   * @param deliveryResults - Array of delivery results
   * @returns The overall notification status
   */
  private determineOverallStatus(deliveryResults: any[]): NotificationStatus {
    if (deliveryResults.length === 0) {
      return NotificationStatus.FAILED;
    }

    const successCount = deliveryResults.filter(result => result.success).length;

    if (successCount === 0) {
      return NotificationStatus.FAILED;
    }

    if (successCount === deliveryResults.length) {
      return NotificationStatus.DELIVERED;
    }

    return NotificationStatus.PARTIALLY_DELIVERED;
  }

  /**
   * Schedules retries for failed notification deliveries.
   * 
   * @param notification - Notification object to retry
   * @param deliveryResults - Array of delivery results
   */
  private async scheduleRetries(notification: INotification, deliveryResults: any[]): Promise<void> {
    // Filter for failed deliveries
    const failedDeliveries = deliveryResults.filter(result => !result.success);

    if (failedDeliveries.length === 0) {
      return;
    }

    this.logger.info('Scheduling retries for failed deliveries', {
      notificationId: notification.id,
      failedCount: failedDeliveries.length,
    });

    // Schedule retries for each failed delivery
    for (const delivery of failedDeliveries) {
      try {
        await this.retryService.scheduleRetry(notification, delivery.recipient, delivery.error);
      } catch (error) {
        this.logger.error('Failed to schedule retry', {
          notificationId: notification.id,
          recipientType: delivery.recipient.type,
          error,
        });
      }
    }
  }

  /**
   * Gets the redelivery count from a RabbitMQ message.
   * 
   * @param msg - RabbitMQ message
   * @returns The number of times the message has been redelivered
   */
  private getRedeliveryCount(msg: ConsumeMessage): number {
    // Check for x-death header which contains redelivery information
    const headers = msg.properties.headers || {};
    const xDeath = headers['x-death'] || [];

    if (xDeath.length > 0 && xDeath[0].count) {
      return xDeath[0].count;
    }

    // If x-death header is not available, use a simple approach
    return msg.fields.redelivered ? 1 : 0;
  }

  /**
   * Sends a message to the dead letter queue for manual inspection.
   * 
   * @param msg - RabbitMQ message to send to DLQ
   */
  private async sendToDeadLetterQueue(msg: ConsumeMessage): Promise<void> {
    if (!this.channel) {
      return;
    }

    try {
      // Ensure the dead letter queue exists
      await this.channel.assertQueue(rabbitmqConfig.queues.deadLetter, {
        durable: true,
      });

      // Publish the original message to the dead letter queue
      this.channel.sendToQueue(
        rabbitmqConfig.queues.deadLetter,
        msg.content,
        {
          persistent: true,
          headers: {
            ...msg.properties.headers,
            'x-original-exchange': msg.fields.exchange,
            'x-original-routing-key': msg.fields.routingKey,
            'x-error': 'Exceeded maximum redelivery attempts',
            'x-timestamp': new Date().toISOString(),
          },
        }
      );

      this.logger.info('Message sent to dead letter queue', {
        queue: rabbitmqConfig.queues.deadLetter,
      });
    } catch (error) {
      this.logger.error('Failed to send message to dead letter queue', { error });
    }
  }

  /**
   * Checks if the service is currently processing a message.
   * 
   * @returns True if the service is processing, false otherwise
   */
  public isCurrentlyProcessing(): boolean {
    return this.isProcessing;
  }
}