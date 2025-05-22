import { Logger } from 'winston';
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import nodemailer, { Transporter } from 'nodemailer';
import { v4 as uuidv4 } from 'uuid';

import {
  MessageChannel,
  MessageStatus,
  MessagePriority,
  IMessageTemplate,
  IMessagePayload,
  IMessageDeliveryOptions,
  IMessage,
  IMessageResult
} from '../types/message';
import { IDateValue } from '../types/common';
import { formatTime } from '../utils/format-time';
import { validateMessagePayload } from '../utils/validation';

/**
 * Configuration interface for MessageService
 */
interface MessageServiceConfig {
  logger: Logger;
  email: {
    host: string;
    port: number;
    secure: boolean;
    auth: {
      user: string;
      pass: string;
    };
    from: string;
  };
  sms: {
    apiKey: string;
    apiSecret: string;
    from: string;
    baseUrl: string;
  };
  push: {
    apiKey: string;
    projectId: string;
    baseUrl: string;
  };
  rateLimits: {
    email: number; // messages per minute
    sms: number;   // messages per minute
    push: number;  // messages per minute
  };
  templates: {
    basePath: string;
    cacheEnabled: boolean;
    cacheTTL: number; // in seconds
  };
}

/**
 * Service responsible for handling different types of notification messages (email, SMS, push).
 * It formats messages according to channel-specific requirements, integrates with external
 * delivery providers, and manages delivery status tracking.
 */
export class MessageService {
  private logger: Logger;
  private config: MessageServiceConfig;
  private emailTransporter: Transporter;
  private smsClient: AxiosInstance;
  private pushClient: AxiosInstance;
  private templateCache: Map<string, IMessageTemplate>;
  private rateLimitCounters: Map<MessageChannel, {
    count: number;
    resetAt: Date;
  }>;

  /**
   * Creates a new instance of MessageService
   * @param config - Configuration for the message service
   */
  constructor(config: MessageServiceConfig) {
    this.logger = config.logger;
    this.config = config;
    this.templateCache = new Map<string, IMessageTemplate>();
    this.rateLimitCounters = new Map<MessageChannel, { count: number; resetAt: Date }>();
    
    // Initialize rate limit counters
    this.initializeRateLimitCounters();
    
    // Initialize email transporter
    this.emailTransporter = nodemailer.createTransport({
      host: config.email.host,
      port: config.email.port,
      secure: config.email.secure,
      auth: {
        user: config.email.auth.user,
        pass: config.email.auth.pass,
      },
    });
    
    // Initialize SMS client
    this.smsClient = axios.create({
      baseURL: config.sms.baseUrl,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Basic ${Buffer.from(`${config.sms.apiKey}:${config.sms.apiSecret}`).toString('base64')}`,
      },
    });
    
    // Initialize Push notification client
    this.pushClient = axios.create({
      baseURL: config.push.baseUrl,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.push.apiKey}`,
      },
    });
    
    this.logger.info('MessageService initialized');
  }

  /**
   * Initializes rate limit counters for each channel
   */
  private initializeRateLimitCounters(): void {
    const resetAt = new Date();
    resetAt.setMinutes(resetAt.getMinutes() + 1);
    
    this.rateLimitCounters.set(MessageChannel.EMAIL, { count: 0, resetAt });
    this.rateLimitCounters.set(MessageChannel.SMS, { count: 0, resetAt });
    this.rateLimitCounters.set(MessageChannel.PUSH, { count: 0, resetAt });
  }

  /**
   * Checks if a message can be sent based on rate limits
   * @param channel - The message channel to check
   * @returns boolean indicating if the message can be sent
   */
  private checkRateLimit(channel: MessageChannel): boolean {
    const counter = this.rateLimitCounters.get(channel);
    if (!counter) return true;
    
    const now = new Date();
    
    // Reset counter if the reset time has passed
    if (now > counter.resetAt) {
      const resetAt = new Date();
      resetAt.setMinutes(resetAt.getMinutes() + 1);
      this.rateLimitCounters.set(channel, { count: 0, resetAt });
      return true;
    }
    
    // Check if the counter is below the limit
    const limit = this.getChannelRateLimit(channel);
    return counter.count < limit;
  }

  /**
   * Increments the rate limit counter for a channel
   * @param channel - The message channel to increment
   */
  private incrementRateLimit(channel: MessageChannel): void {
    const counter = this.rateLimitCounters.get(channel);
    if (!counter) return;
    
    counter.count += 1;
    this.rateLimitCounters.set(channel, counter);
  }

  /**
   * Gets the rate limit for a specific channel
   * @param channel - The message channel
   * @returns The rate limit for the channel
   */
  private getChannelRateLimit(channel: MessageChannel): number {
    switch (channel) {
      case MessageChannel.EMAIL:
        return this.config.rateLimits.email;
      case MessageChannel.SMS:
        return this.config.rateLimits.sms;
      case MessageChannel.PUSH:
        return this.config.rateLimits.push;
      default:
        return Number.MAX_SAFE_INTEGER; // No limit for other channels
    }
  }

  /**
   * Creates a new message
   * @param channel - The message channel
   * @param recipient - The recipient address
   * @param payload - The message payload
   * @param options - Delivery options
   * @param metadata - Additional message metadata
   * @returns The created message
   */
  public createMessage(
    channel: MessageChannel,
    recipient: string,
    payload: IMessagePayload,
    options: Partial<IMessageDeliveryOptions> = {},
    metadata?: Record<string, any>
  ): IMessage {
    // Validate the payload
    validateMessagePayload(channel, payload);
    
    const now: IDateValue = {
      value: formatTime(new Date()),
    };
    
    // Set default delivery options
    const deliveryOptions: IMessageDeliveryOptions = {
      priority: options.priority || MessagePriority.MEDIUM,
      maxRetries: options.maxRetries !== undefined ? options.maxRetries : 3,
      retryInterval: options.retryInterval || 60000, // 1 minute
      retryStrategy: options.retryStrategy || 'exponential',
      requireConfirmation: options.requireConfirmation !== undefined ? options.requireConfirmation : false,
      idempotencyKey: options.idempotencyKey || uuidv4(),
      provider: options.provider,
      providerOptions: options.providerOptions || {},
      encryptContent: options.encryptContent !== undefined ? options.encryptContent : false,
      signatureRequired: options.signatureRequired !== undefined ? options.signatureRequired : false,
    };
    
    // Create the message
    const message: IMessage = {
      id: uuidv4(),
      channel,
      status: MessageStatus.QUEUED,
      recipient,
      payload,
      deliveryOptions,
      createdAt: now,
      updatedAt: now,
      retryCount: 0,
    };
    
    // Add metadata if provided
    if (metadata) {
      message.metadata = {
        correlationId: metadata.correlationId || uuidv4(),
        ...metadata,
      };
    }
    
    this.logger.debug(`Message created: ${message.id}`, { messageId: message.id, channel });
    
    return message;
  }

  /**
   * Creates a message from a template
   * @param templateId - The template ID
   * @param recipient - The recipient address
   * @param variables - Template variables
   * @param options - Delivery options
   * @param metadata - Additional message metadata
   * @returns The created message
   */
  public async createMessageFromTemplate(
    templateId: string,
    recipient: string,
    variables: Record<string, any>,
    options: Partial<IMessageDeliveryOptions> = {},
    metadata?: Record<string, any>
  ): Promise<IMessage> {
    // Get the template
    const template = await this.getTemplate(templateId);
    if (!template) {
      throw new Error(`Template not found: ${templateId}`);
    }
    
    // Apply template variables
    const payload = this.applyTemplateVariables(template, variables);
    
    // Create the message
    return this.createMessage(
      template.channel,
      recipient,
      payload,
      options,
      {
        templateId,
        ...metadata,
      }
    );
  }

  /**
   * Gets a template by ID
   * @param templateId - The template ID
   * @returns The template or null if not found
   */
  private async getTemplate(templateId: string): Promise<IMessageTemplate | null> {
    // Check cache first if enabled
    if (this.config.templates.cacheEnabled) {
      const cachedTemplate = this.templateCache.get(templateId);
      if (cachedTemplate) {
        return cachedTemplate;
      }
    }
    
    // TODO: Implement template retrieval from database or file system
    // For now, we'll return a mock template for demonstration
    const mockTemplate: IMessageTemplate = {
      id: templateId,
      name: 'Mock Template',
      description: 'A mock template for demonstration',
      channel: MessageChannel.EMAIL,
      subject: 'Mock Subject',
      body: 'Hello {{name}}, this is a mock template with {{variable}}.',
      variables: ['name', 'variable'],
      createdAt: { value: formatTime(new Date()) },
      updatedAt: { value: formatTime(new Date()) },
      version: 1,
      isActive: true,
    };
    
    // Cache the template if caching is enabled
    if (this.config.templates.cacheEnabled) {
      this.templateCache.set(templateId, mockTemplate);
      
      // Set cache expiration
      setTimeout(() => {
        this.templateCache.delete(templateId);
      }, this.config.templates.cacheTTL * 1000);
    }
    
    return mockTemplate;
  }

  /**
   * Applies template variables to a template
   * @param template - The message template
   * @param variables - The variables to apply
   * @returns The message payload with variables applied
   */
  private applyTemplateVariables(
    template: IMessageTemplate,
    variables: Record<string, any>
  ): IMessagePayload {
    let body = template.body;
    let subject = template.subject || '';
    
    // Replace variables in the body
    for (const key in variables) {
      const regex = new RegExp(`{{${key}}}`, 'g');
      body = body.replace(regex, variables[key]);
      if (subject) {
        subject = subject.replace(regex, variables[key]);
      }
    }
    
    // Create the payload
    const payload: IMessagePayload = {
      body,
      variables,
    };
    
    // Add channel-specific fields
    if (template.channel === MessageChannel.EMAIL) {
      payload.subject = subject;
      payload.htmlBody = body; // Assuming the template body is HTML
    } else if (template.channel === MessageChannel.PUSH) {
      payload.title = subject;
    }
    
    return payload;
  }

  /**
   * Sends a message
   * @param message - The message to send
   * @returns The message result
   */
  public async sendMessage(message: IMessage): Promise<IMessageResult> {
    this.logger.debug(`Sending message: ${message.id}`, { messageId: message.id, channel: message.channel });
    
    // Check rate limits
    if (!this.checkRateLimit(message.channel)) {
      this.logger.warn(`Rate limit exceeded for channel: ${message.channel}`, {
        messageId: message.id,
        channel: message.channel,
      });
      
      return {
        messageId: message.id,
        success: false,
        status: MessageStatus.FAILED,
        timestamp: { value: formatTime(new Date()) },
        errorCode: 'RATE_LIMIT_EXCEEDED',
        errorMessage: `Rate limit exceeded for channel: ${message.channel}`,
        retryable: true,
      };
    }
    
    // Increment rate limit counter
    this.incrementRateLimit(message.channel);
    
    // Update message status
    message.status = MessageStatus.SENT;
    message.sentAt = { value: formatTime(new Date()) };
    
    try {
      // Send the message based on the channel
      let result: IMessageResult;
      
      switch (message.channel) {
        case MessageChannel.EMAIL:
          result = await this.sendEmailMessage(message);
          break;
        case MessageChannel.SMS:
          result = await this.sendSmsMessage(message);
          break;
        case MessageChannel.PUSH:
          result = await this.sendPushMessage(message);
          break;
        default:
          throw new Error(`Unsupported message channel: ${message.channel}`);
      }
      
      // Update message status based on result
      message.status = result.status;
      message.updatedAt = { value: formatTime(new Date()) };
      
      if (result.success) {
        message.deliveredAt = { value: formatTime(new Date()) };
      } else {
        message.failedAt = { value: formatTime(new Date()) };
        message.errorDetails = result.errorMessage;
        message.retryCount = (message.retryCount || 0) + 1;
        
        // Calculate next retry time if retryable
        if (result.retryable && message.retryCount < (message.deliveryOptions.maxRetries || 3)) {
          const retryInterval = this.calculateRetryInterval(
            message.deliveryOptions.retryInterval || 60000,
            message.retryCount,
            message.deliveryOptions.retryStrategy || 'exponential'
          );
          
          const nextRetryDate = new Date();
          nextRetryDate.setMilliseconds(nextRetryDate.getMilliseconds() + retryInterval);
          
          message.nextRetryAt = { value: formatTime(nextRetryDate) };
        }
      }
      
      return result;
    } catch (error) {
      this.logger.error(`Error sending message: ${message.id}`, {
        messageId: message.id,
        channel: message.channel,
        error: error instanceof Error ? error.message : String(error),
      });
      
      // Update message status
      message.status = MessageStatus.FAILED;
      message.updatedAt = { value: formatTime(new Date()) };
      message.failedAt = { value: formatTime(new Date()) };
      message.errorDetails = error instanceof Error ? error.message : String(error);
      message.retryCount = (message.retryCount || 0) + 1;
      
      // Calculate next retry time
      if (message.retryCount < (message.deliveryOptions.maxRetries || 3)) {
        const retryInterval = this.calculateRetryInterval(
          message.deliveryOptions.retryInterval || 60000,
          message.retryCount,
          message.deliveryOptions.retryStrategy || 'exponential'
        );
        
        const nextRetryDate = new Date();
        nextRetryDate.setMilliseconds(nextRetryDate.getMilliseconds() + retryInterval);
        
        message.nextRetryAt = { value: formatTime(nextRetryDate) };
      }
      
      return {
        messageId: message.id,
        success: false,
        status: MessageStatus.FAILED,
        timestamp: { value: formatTime(new Date()) },
        errorCode: 'DELIVERY_ERROR',
        errorMessage: error instanceof Error ? error.message : String(error),
        retryable: true,
      };
    }
  }

  /**
   * Calculates the retry interval based on the retry strategy
   * @param baseInterval - The base retry interval in milliseconds
   * @param retryCount - The current retry count
   * @param strategy - The retry strategy (linear or exponential)
   * @returns The calculated retry interval in milliseconds
   */
  private calculateRetryInterval(
    baseInterval: number,
    retryCount: number,
    strategy: 'linear' | 'exponential'
  ): number {
    if (strategy === 'linear') {
      return baseInterval * (retryCount + 1);
    } else {
      // Exponential backoff with jitter
      const exponentialInterval = baseInterval * Math.pow(2, retryCount);
      const jitter = Math.random() * 0.3 * exponentialInterval; // 30% jitter
      return exponentialInterval + jitter;
    }
  }

  /**
   * Sends an email message
   * @param message - The message to send
   * @returns The message result
   */
  private async sendEmailMessage(message: IMessage): Promise<IMessageResult> {
    this.logger.debug(`Sending email message: ${message.id}`, { messageId: message.id });
    
    try {
      // Prepare email options
      const mailOptions = {
        from: this.config.email.from,
        to: message.recipient,
        subject: message.payload.subject || 'No Subject',
        text: message.payload.body,
        html: message.payload.htmlBody || message.payload.body,
        attachments: message.payload.attachments?.map(attachment => ({
          filename: attachment.name,
          contentType: attachment.contentType,
          content: attachment.content,
        })),
      };
      
      // Send the email
      const info = await this.emailTransporter.sendMail(mailOptions);
      
      this.logger.info(`Email sent: ${message.id}`, {
        messageId: message.id,
        emailId: info.messageId,
      });
      
      return {
        messageId: message.id,
        success: true,
        status: MessageStatus.DELIVERED,
        timestamp: { value: formatTime(new Date()) },
        providerMessageId: info.messageId,
        providerResponse: JSON.stringify(info),
        deliveryMetrics: {
          latency: 0, // Not available for email
          size: Buffer.byteLength(message.payload.body, 'utf8'),
        },
      };
    } catch (error) {
      this.logger.error(`Error sending email: ${message.id}`, {
        messageId: message.id,
        error: error instanceof Error ? error.message : String(error),
      });
      
      return {
        messageId: message.id,
        success: false,
        status: MessageStatus.FAILED,
        timestamp: { value: formatTime(new Date()) },
        errorCode: 'EMAIL_DELIVERY_ERROR',
        errorMessage: error instanceof Error ? error.message : String(error),
        retryable: this.isRetryableEmailError(error),
      };
    }
  }

  /**
   * Determines if an email error is retryable
   * @param error - The error to check
   * @returns Whether the error is retryable
   */
  private isRetryableEmailError(error: unknown): boolean {
    if (!(error instanceof Error)) return true;
    
    // Non-retryable errors
    const nonRetryableErrors = [
      'invalid address',
      'domain not found',
      'mailbox unavailable',
      'user unknown',
      'rejected recipient',
    ];
    
    const errorMessage = error.message.toLowerCase();
    
    // Check if the error message contains any non-retryable phrases
    return !nonRetryableErrors.some(phrase => errorMessage.includes(phrase));
  }

  /**
   * Sends an SMS message
   * @param message - The message to send
   * @returns The message result
   */
  private async sendSmsMessage(message: IMessage): Promise<IMessageResult> {
    this.logger.debug(`Sending SMS message: ${message.id}`, { messageId: message.id });
    
    try {
      // Prepare SMS payload
      const smsPayload = {
        from: message.payload.senderName || this.config.sms.from,
        to: message.recipient,
        text: message.payload.body,
      };
      
      // Send the SMS
      const startTime = Date.now();
      const response = await this.smsClient.post('/messages', smsPayload);
      const latency = Date.now() - startTime;
      
      this.logger.info(`SMS sent: ${message.id}`, {
        messageId: message.id,
        smsId: response.data.id,
      });
      
      return {
        messageId: message.id,
        success: true,
        status: MessageStatus.DELIVERED,
        timestamp: { value: formatTime(new Date()) },
        providerMessageId: response.data.id,
        providerResponse: JSON.stringify(response.data),
        deliveryMetrics: {
          latency,
          size: Buffer.byteLength(message.payload.body, 'utf8'),
          cost: response.data.cost,
        },
      };
    } catch (error) {
      this.logger.error(`Error sending SMS: ${message.id}`, {
        messageId: message.id,
        error: error instanceof Error ? error.message : String(error),
      });
      
      return {
        messageId: message.id,
        success: false,
        status: MessageStatus.FAILED,
        timestamp: { value: formatTime(new Date()) },
        errorCode: 'SMS_DELIVERY_ERROR',
        errorMessage: error instanceof Error ? error.message : String(error),
        retryable: this.isRetryableSmsError(error),
      };
    }
  }

  /**
   * Determines if an SMS error is retryable
   * @param error - The error to check
   * @returns Whether the error is retryable
   */
  private isRetryableSmsError(error: unknown): boolean {
    if (!(error instanceof Error)) return true;
    
    // Non-retryable errors
    const nonRetryableErrors = [
      'invalid number',
      'unroutable',
      'rejected',
      'blocked',
    ];
    
    const errorMessage = error.message.toLowerCase();
    
    // Check if the error message contains any non-retryable phrases
    return !nonRetryableErrors.some(phrase => errorMessage.includes(phrase));
  }

  /**
   * Sends a push notification message
   * @param message - The message to send
   * @returns The message result
   */
  private async sendPushMessage(message: IMessage): Promise<IMessageResult> {
    this.logger.debug(`Sending push message: ${message.id}`, { messageId: message.id });
    
    try {
      // Prepare push notification payload
      const pushPayload = {
        token: message.recipient, // Device token
        notification: {
          title: message.payload.title || 'Notification',
          body: message.payload.body,
          imageUrl: message.payload.imageUrl,
        },
        data: {
          deepLink: message.payload.deepLink,
          ...message.metadata,
        },
        android: {
          priority: message.deliveryOptions.priority === MessagePriority.HIGH ? 'high' : 'normal',
        },
        apns: {
          headers: {
            'apns-priority': message.deliveryOptions.priority === MessagePriority.HIGH ? '10' : '5',
          },
        },
      };
      
      // Send the push notification
      const startTime = Date.now();
      const response = await this.pushClient.post('/messages:send', {
        message: pushPayload,
        validateOnly: false,
      });
      const latency = Date.now() - startTime;
      
      this.logger.info(`Push notification sent: ${message.id}`, {
        messageId: message.id,
        pushId: response.data.name,
      });
      
      return {
        messageId: message.id,
        success: true,
        status: MessageStatus.SENT, // Push notifications can only confirm sending, not delivery
        timestamp: { value: formatTime(new Date()) },
        providerMessageId: response.data.name,
        providerResponse: JSON.stringify(response.data),
        deliveryMetrics: {
          latency,
          size: Buffer.byteLength(JSON.stringify(pushPayload), 'utf8'),
        },
      };
    } catch (error) {
      this.logger.error(`Error sending push notification: ${message.id}`, {
        messageId: message.id,
        error: error instanceof Error ? error.message : String(error),
      });
      
      return {
        messageId: message.id,
        success: false,
        status: MessageStatus.FAILED,
        timestamp: { value: formatTime(new Date()) },
        errorCode: 'PUSH_DELIVERY_ERROR',
        errorMessage: error instanceof Error ? error.message : String(error),
        retryable: this.isRetryablePushError(error),
      };
    }
  }

  /**
   * Determines if a push notification error is retryable
   * @param error - The error to check
   * @returns Whether the error is retryable
   */
  private isRetryablePushError(error: unknown): boolean {
    if (!(error instanceof Error)) return true;
    
    // Non-retryable errors
    const nonRetryableErrors = [
      'invalid token',
      'unregistered',
      'not found',
    ];
    
    const errorMessage = error.message.toLowerCase();
    
    // Check if the error message contains any non-retryable phrases
    return !nonRetryableErrors.some(phrase => errorMessage.includes(phrase));
  }

  /**
   * Gets the delivery status of a message
   * @param messageId - The message ID
   * @returns The message status or null if not found
   */
  public async getMessageStatus(messageId: string): Promise<MessageStatus | null> {
    // TODO: Implement message status retrieval from database
    // For now, we'll return a mock status
    return MessageStatus.DELIVERED;
  }

  /**
   * Gets a message by ID
   * @param messageId - The message ID
   * @returns The message or null if not found
   */
  public async getMessage(messageId: string): Promise<IMessage | null> {
    // TODO: Implement message retrieval from database
    // For now, we'll return null
    return null;
  }

  /**
   * Updates a message
   * @param message - The message to update
   * @returns The updated message
   */
  public async updateMessage(message: IMessage): Promise<IMessage> {
    // TODO: Implement message update in database
    // For now, we'll just return the message
    message.updatedAt = { value: formatTime(new Date()) };
    return message;
  }
}