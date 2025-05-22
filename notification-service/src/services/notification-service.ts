import { Channel, ConsumeMessage } from 'amqplib';
import { Logger } from 'winston';

import { config } from '../config';
import { logger } from '../config/logger';
import {
  IRabbitMQMessage,
  NotificationType,
  INotification,
  INotificationPayload,
  INotificationRecipient,
  MessageChannel,
  IRetryOptions,
  ILogContext
} from '../types';
import { WebhookService } from './webhook-service';
import { MessageService } from './message-service';
import { RetryService } from './retry-service';
import { AuditService } from './audit-service';

/**
 * Core service that processes notification messages from RabbitMQ, determines notification types,
 * resolves recipients, and orchestrates the delivery process. It acts as the central coordinator
 * for the notification system, consuming messages from the notification queue and delegating to
 * specialized services for delivery.
 */
export class NotificationService {
  private channel: Channel | null = null;
  private readonly logger: Logger;
  private readonly webhookService: WebhookService;
  private readonly messageService: MessageService;
  private readonly retryService: RetryService;
  private readonly auditService: AuditService;
  private readonly consumerTag: string;
  private isConsuming: boolean = false;

  /**
   * Creates a new instance of the NotificationService.
   * 
   * @param channel - RabbitMQ channel for consuming messages
   * @param webhookService - Service for webhook delivery
   * @param messageService - Service for email, SMS, and push notifications
   * @param retryService - Service for handling retry logic
   * @param auditService - Service for logging audit records
   * @param logContext - Logging context for correlation
   */
  constructor(
    channel: Channel,
    webhookService: WebhookService,
    messageService: MessageService,
    retryService: RetryService,
    auditService: AuditService,
    private readonly logContext: ILogContext = {}
  ) {
    this.channel = channel;
    this.webhookService = webhookService;
    this.messageService = messageService;
    this.retryService = retryService;
    this.auditService = auditService;
    this.logger = logger.child({ ...logContext, service: 'NotificationService' });
    this.consumerTag = `notification-consumer-${Date.now()}`;
  }

  /**
   * Starts consuming messages from the notification queue.
   * 
   * @returns Promise that resolves when the consumer is registered
   */
  public async startConsuming(): Promise<void> {
    if (!this.channel) {
      throw new Error('RabbitMQ channel is not initialized');
    }

    if (this.isConsuming) {
      this.logger.warn('Already consuming messages from the notification queue');
      return;
    }

    try {
      // Ensure the queue exists
      await this.channel.assertQueue(config.rabbitmq.queues.notification, {
        durable: true,
      });

      // Start consuming messages
      await this.channel.consume(
        config.rabbitmq.queues.notification,
        this.handleMessage.bind(this),
        { consumerTag: this.consumerTag }
      );

      this.isConsuming = true;
      this.logger.info('Started consuming messages from the notification queue');
    } catch (error) {
      this.logger.error('Failed to start consuming messages', { error });
      throw error;
    }
  }

  /**
   * Stops consuming messages from the notification queue.
   * 
   * @returns Promise that resolves when the consumer is cancelled
   */
  public async stopConsuming(): Promise<void> {
    if (!this.channel || !this.isConsuming) {
      return;
    }

    try {
      await this.channel.cancel(this.consumerTag);
      this.isConsuming = false;
      this.logger.info('Stopped consuming messages from the notification queue');
    } catch (error) {
      this.logger.error('Failed to stop consuming messages', { error });
      throw error;
    }
  }

  /**
   * Handles an incoming message from the notification queue.
   * 
   * @param message - The RabbitMQ message to process
   */
  private async handleMessage(message: ConsumeMessage | null): Promise<void> {
    if (!message || !this.channel) {
      return;
    }

    const messageId = message.properties.messageId || 'unknown';
    const correlationId = message.properties.correlationId || 'unknown';
    const logContext = { ...this.logContext, messageId, correlationId };
    const childLogger = this.logger.child(logContext);

    try {
      childLogger.info('Received notification message');

      // Parse the message content
      const content = message.content.toString();
      const rabbitMQMessage = JSON.parse(content) as IRabbitMQMessage;

      // Process the notification
      await this.processNotification(rabbitMQMessage, logContext);

      // Acknowledge the message
      this.channel.ack(message);
      childLogger.info('Successfully processed notification message');
    } catch (error) {
      childLogger.error('Failed to process notification message', { error });

      // Negative acknowledge the message to requeue it
      // Only requeue if it hasn't been redelivered too many times
      const redelivered = message.fields.redelivered;
      const redeliveryCount = message.properties.headers?.['x-redelivery-count'] || 0;

      if (redelivered && redeliveryCount >= config.rabbitmq.maxRedeliveries) {
        childLogger.warn('Message exceeded max redeliveries, sending to dead letter queue');
        this.channel.nack(message, false, false);
      } else {
        childLogger.info('Requeueing message for retry');
        this.channel.nack(message, false, true);
      }
    }
  }

  /**
   * Processes a notification message and delegates to appropriate delivery services.
   * 
   * @param message - The parsed RabbitMQ message
   * @param logContext - Logging context for correlation
   */
  private async processNotification(
    message: IRabbitMQMessage,
    logContext: ILogContext
  ): Promise<void> {
    const childLogger = this.logger.child(logContext);
    
    // Validate the message structure
    if (!message.payload || !message.metadata) {
      throw new Error('Invalid notification message structure');
    }

    // Determine notification type
    const notificationType = this.determineNotificationType(message);
    childLogger.info('Determined notification type', { notificationType });

    // Create notification payload
    const payload = this.createNotificationPayload(message, notificationType);
    
    // Resolve recipients
    const recipients = await this.resolveRecipients(message, notificationType);
    childLogger.info('Resolved recipients', { recipientCount: recipients.length });

    if (recipients.length === 0) {
      childLogger.warn('No recipients found for notification');
      return;
    }

    // Create notification object
    const notification: INotification = {
      id: message.metadata.id || `notification-${Date.now()}`,
      type: notificationType,
      status: 'PENDING',
      priority: this.determinePriority(notificationType),
      payload,
      recipients,
      metadata: {
        ...message.metadata,
        processedAt: new Date().toISOString(),
      },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    // Log the notification for audit purposes
    await this.auditService.logNotification(notification, logContext);

    // Process each recipient
    const deliveryPromises = recipients.map(recipient => 
      this.deliverNotification(notification, recipient, logContext)
    );

    // Wait for all deliveries to complete
    await Promise.all(deliveryPromises);
  }

  /**
   * Determines the notification type based on the message content.
   * 
   * @param message - The parsed RabbitMQ message
   * @returns The determined notification type
   */
  private determineNotificationType(message: IRabbitMQMessage): NotificationType {
    // Check for explicit type in metadata
    if (message.metadata.notificationType) {
      return message.metadata.notificationType as NotificationType;
    }

    // Check for status updates
    if (message.payload.status || message.metadata.status) {
      return NotificationType.STATUS_UPDATE;
    }

    // Check for errors
    if (message.payload.error || message.metadata.error) {
      return NotificationType.ERROR;
    }

    // Check for completion
    if (
      message.payload.status === 'COMPLETED' ||
      message.metadata.status === 'COMPLETED' ||
      message.payload.completed === true ||
      message.metadata.completed === true
    ) {
      return NotificationType.COMPLETION;
    }

    // Default to status update
    return NotificationType.STATUS_UPDATE;
  }

  /**
   * Creates a notification payload from the message content.
   * 
   * @param message - The parsed RabbitMQ message
   * @param type - The notification type
   * @returns The notification payload
   */
  private createNotificationPayload(
    message: IRabbitMQMessage,
    type: NotificationType
  ): INotificationPayload {
    // Start with the original payload
    const payload: INotificationPayload = {
      ...message.payload,
      notificationType: type,
    };

    // Add application data if available
    if (message.metadata.applicationId) {
      payload.applicationId = message.metadata.applicationId;
    }

    // Add status information if available
    if (message.metadata.status) {
      payload.status = message.metadata.status;
    }

    // Add error information if available
    if (message.metadata.error) {
      payload.error = message.metadata.error;
    }

    // Add timestamp
    payload.timestamp = new Date().toISOString();

    return payload;
  }

  /**
   * Resolves the recipients for a notification based on the message content and type.
   * 
   * @param message - The parsed RabbitMQ message
   * @param type - The notification type
   * @returns Promise that resolves to an array of notification recipients
   */
  private async resolveRecipients(
    message: IRabbitMQMessage,
    type: NotificationType
  ): Promise<INotificationRecipient[]> {
    const recipients: INotificationRecipient[] = [];

    // Check for explicit recipients in the message
    if (message.recipients && Array.isArray(message.recipients)) {
      return message.recipients;
    }

    // Check for webhook configurations in metadata
    if (message.metadata.webhookIds && Array.isArray(message.metadata.webhookIds)) {
      const webhookIds = message.metadata.webhookIds as string[];
      
      for (const webhookId of webhookIds) {
        recipients.push({
          type: 'WEBHOOK',
          webhookId,
          active: true,
        });
      }
    }

    // Check for application ID and resolve configured webhooks
    if (message.metadata.applicationId) {
      const applicationId = message.metadata.applicationId as string;
      
      // Get webhooks configured for this application
      const webhooks = await this.webhookService.getWebhooksForApplication(applicationId);
      
      for (const webhook of webhooks) {
        // Check if webhook is configured for this notification type
        if (webhook.eventTypes.includes(type) || webhook.eventTypes.includes('ALL')) {
          recipients.push({
            type: 'WEBHOOK',
            webhookId: webhook.id,
            active: webhook.status === 'ACTIVE',
          });
        }
      }
    }

    // Check for email recipients
    if (message.metadata.emailRecipients && Array.isArray(message.metadata.emailRecipients)) {
      const emailRecipients = message.metadata.emailRecipients as string[];
      
      for (const email of emailRecipients) {
        recipients.push({
          type: 'EMAIL',
          email,
          active: true,
        });
      }
    }

    // Check for SMS recipients
    if (message.metadata.smsRecipients && Array.isArray(message.metadata.smsRecipients)) {
      const smsRecipients = message.metadata.smsRecipients as string[];
      
      for (const phone of smsRecipients) {
        recipients.push({
          type: 'SMS',
          phone,
          active: true,
        });
      }
    }

    return recipients;
  }

  /**
   * Determines the priority of a notification based on its type.
   * 
   * @param type - The notification type
   * @returns The notification priority
   */
  private determinePriority(type: NotificationType): 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' {
    switch (type) {
      case NotificationType.ERROR:
        return 'HIGH';
      case NotificationType.COMPLETION:
        return 'MEDIUM';
      case NotificationType.STATUS_UPDATE:
      default:
        return 'LOW';
    }
  }

  /**
   * Delivers a notification to a specific recipient.
   * 
   * @param notification - The notification to deliver
   * @param recipient - The recipient to deliver to
   * @param logContext - Logging context for correlation
   * @returns Promise that resolves when the delivery is complete
   */
  private async deliverNotification(
    notification: INotification,
    recipient: INotificationRecipient,
    logContext: ILogContext
  ): Promise<void> {
    const childLogger = this.logger.child({ ...logContext, recipientType: recipient.type });
    
    // Skip inactive recipients
    if (recipient.active === false) {
      childLogger.info('Skipping inactive recipient');
      return;
    }

    try {
      // Determine the delivery channel
      switch (recipient.type) {
        case 'WEBHOOK':
          if (!recipient.webhookId) {
            throw new Error('Webhook ID is required for webhook recipients');
          }
          
          childLogger.info('Delivering notification via webhook', { webhookId: recipient.webhookId });
          await this.webhookService.deliverWebhook(
            notification,
            recipient.webhookId,
            this.getRetryOptions(notification),
            logContext
          );
          break;

        case 'EMAIL':
          if (!recipient.email) {
            throw new Error('Email address is required for email recipients');
          }
          
          childLogger.info('Delivering notification via email', { email: recipient.email });
          await this.messageService.sendMessage({
            channel: MessageChannel.EMAIL,
            recipient: recipient.email,
            subject: this.getNotificationSubject(notification),
            payload: notification.payload,
            priority: notification.priority,
            metadata: notification.metadata,
          }, logContext);
          break;

        case 'SMS':
          if (!recipient.phone) {
            throw new Error('Phone number is required for SMS recipients');
          }
          
          childLogger.info('Delivering notification via SMS', { phone: recipient.phone });
          await this.messageService.sendMessage({
            channel: MessageChannel.SMS,
            recipient: recipient.phone,
            payload: notification.payload,
            priority: notification.priority,
            metadata: notification.metadata,
          }, logContext);
          break;

        case 'PUSH':
          if (!recipient.deviceToken) {
            throw new Error('Device token is required for push notification recipients');
          }
          
          childLogger.info('Delivering notification via push', { deviceToken: recipient.deviceToken });
          await this.messageService.sendMessage({
            channel: MessageChannel.PUSH,
            recipient: recipient.deviceToken,
            title: this.getNotificationSubject(notification),
            payload: notification.payload,
            priority: notification.priority,
            metadata: notification.metadata,
          }, logContext);
          break;

        default:
          throw new Error(`Unsupported recipient type: ${recipient.type}`);
      }

      childLogger.info('Successfully delivered notification');
    } catch (error) {
      childLogger.error('Failed to deliver notification', { error });
      
      // Check if the error is retryable
      if (this.isRetryableError(error) && notification.metadata.maxRetries !== 0) {
        childLogger.info('Scheduling notification for retry');
        
        // Schedule for retry
        await this.retryService.scheduleRetry(
          notification,
          recipient,
          error,
          this.getRetryOptions(notification),
          logContext
        );
      } else {
        childLogger.warn('Notification delivery failed permanently');
        
        // Log the permanent failure
        await this.auditService.logDeliveryFailure(
          notification,
          recipient,
          error,
          logContext
        );
      }

      // Rethrow the error to be handled by the caller
      throw error;
    }
  }

  /**
   * Gets the subject line for a notification based on its type and content.
   * 
   * @param notification - The notification
   * @returns The subject line for the notification
   */
  private getNotificationSubject(notification: INotification): string {
    const appId = notification.payload.applicationId || notification.metadata.applicationId || 'Unknown';
    
    switch (notification.type) {
      case NotificationType.STATUS_UPDATE:
        const status = notification.payload.status || 'updated';
        return `Application ${appId} status ${status}`;
      
      case NotificationType.ERROR:
        return `Error processing application ${appId}`;
      
      case NotificationType.COMPLETION:
        return `Application ${appId} processing completed`;
      
      default:
        return `Notification for application ${appId}`;
    }
  }

  /**
   * Gets the retry options for a notification based on its metadata.
   * 
   * @param notification - The notification
   * @returns The retry options
   */
  private getRetryOptions(notification: INotification): IRetryOptions {
    return {
      maxRetries: notification.metadata.maxRetries ?? config.retry.maxRetries,
      initialDelay: notification.metadata.initialRetryDelay ?? config.retry.initialDelay,
      maxDelay: notification.metadata.maxRetryDelay ?? config.retry.maxDelay,
      backoffFactor: notification.metadata.retryBackoffFactor ?? config.retry.backoffFactor,
      jitter: notification.metadata.retryJitter ?? config.retry.jitter,
    };
  }

  /**
   * Determines if an error is retryable based on its type and properties.
   * 
   * @param error - The error to check
   * @returns True if the error is retryable, false otherwise
   */
  private isRetryableError(error: any): boolean {
    // Network errors are generally retryable
    if (error.code === 'ECONNREFUSED' || 
        error.code === 'ECONNRESET' || 
        error.code === 'ETIMEDOUT' || 
        error.code === 'ENETUNREACH') {
      return true;
    }

    // HTTP 5xx errors are generally retryable
    if (error.status >= 500 && error.status < 600) {
      return true;
    }

    // HTTP 429 (Too Many Requests) is retryable
    if (error.status === 429) {
      return true;
    }

    // Some HTTP 4xx errors are not retryable
    if (error.status >= 400 && error.status < 500) {
      // These specific 4xx errors are not retryable
      if (error.status === 400 || // Bad Request
          error.status === 401 || // Unauthorized
          error.status === 403 || // Forbidden
          error.status === 404 || // Not Found
          error.status === 410) { // Gone
        return false;
      }
    }

    // Check for explicit non-retryable flag
    if (error.retryable === false) {
      return false;
    }

    // Default to retryable for unknown errors
    return true;
  }
}