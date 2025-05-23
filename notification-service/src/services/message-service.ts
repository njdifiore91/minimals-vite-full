import { Logger } from 'winston';
import nodemailer from 'nodemailer';
import axios from 'axios';
import {
  IMessage,
  IMessagePayload,
  IMessageResult,
  IMessageTemplate,
  MessageChannel,
  MessageStatus,
  MessagePriority
} from '../types/message';
import { formatTime } from '../utils/format-time';
import { isValidEmail, isValidPhoneNumber } from '../utils/validation';

/**
 * Configuration interface for MessageService
 */
interface MessageServiceConfig {
  logger: Logger;
  email?: {
    host: string;
    port: number;
    secure: boolean;
    auth: {
      user: string;
      pass: string;
    };
    from: string;
  };
  sms?: {
    provider: string;
    apiKey: string;
    from: string;
  };
  push?: {
    provider: string;
    apiKey: string;
    vapidKeys?: {
      publicKey: string;
      privateKey: string;
    };
  };
  templates?: {
    basePath: string;
  };
  rateLimits?: {
    email: number; // messages per minute
    sms: number;   // messages per minute
    push: number;  // messages per minute
  };
}

/**
 * Service that handles different types of notification messages (email, SMS, push).
 * It formats messages according to channel-specific requirements, integrates with
 * external delivery providers, and manages delivery status tracking.
 */
export class MessageService {
  private logger: Logger;
  private config: MessageServiceConfig;
  private emailTransporter: nodemailer.Transporter | null = null;
  private templates: Map<string, IMessageTemplate> = new Map();
  private rateLimitCounters: Map<string, { count: number; resetAt: Date }> = new Map();

  /**
   * Creates an instance of MessageService.
   * @param config - Configuration for the message service
   */
  constructor(config: MessageServiceConfig) {
    this.logger = config.logger;
    this.config = config;
    this.initialize();
  }

  /**
   * Initializes the message service, setting up transporters and loading templates
   */
  private async initialize(): Promise<void> {
    try {
      // Initialize email transporter if configured
      if (this.config.email) {
        this.emailTransporter = nodemailer.createTransport({
          host: this.config.email.host,
          port: this.config.email.port,
          secure: this.config.email.secure,
          auth: {
            user: this.config.email.auth.user,
            pass: this.config.email.auth.pass,
          },
        });

        // Verify email connection
        await this.emailTransporter.verify();
        this.logger.info('Email transporter initialized successfully');
      }

      // Initialize SMS provider if configured
      if (this.config.sms) {
        this.logger.info(`SMS provider ${this.config.sms.provider} initialized`);
      }

      // Initialize push notification provider if configured
      if (this.config.push) {
        this.logger.info(`Push notification provider ${this.config.push.provider} initialized`);
      }

      // Load message templates if configured
      if (this.config.templates) {
        await this.loadTemplates();
      }

      this.logger.info('MessageService initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize MessageService', { error });
      throw error;
    }
  }

  /**
   * Loads message templates from the configured templates path
   */
  private async loadTemplates(): Promise<void> {
    try {
      // In a real implementation, this would load templates from files or a database
      // For now, we'll just log that templates would be loaded
      this.logger.info('Templates would be loaded from configured path');
      
      // Example of how templates might be loaded and stored
      // const templateFiles = await fs.readdir(this.config.templates.basePath);
      // for (const file of templateFiles) {
      //   const template = await fs.readFile(path.join(this.config.templates.basePath, file), 'utf8');
      //   const parsedTemplate = JSON.parse(template) as IMessageTemplate;
      //   this.templates.set(parsedTemplate.id, parsedTemplate);
      // }
      
      this.logger.info('Templates loaded successfully');
    } catch (error) {
      this.logger.error('Failed to load templates', { error });
      throw error;
    }
  }

  /**
   * Sends a message through the specified channel
   * @param message - The message to send
   * @returns A promise that resolves to the message result
   */
  public async sendMessage(message: IMessage): Promise<IMessageResult> {
    try {
      // Validate the message
      this.validateMessage(message);

      // Check rate limits
      if (!this.checkRateLimit(message.channel)) {
        return this.createFailedResult(
          message.id,
          'Rate limit exceeded for channel: ' + message.channel
        );
      }

      // Process template if templateId is provided
      if (message.templateId) {
        message = await this.processTemplate(message);
      }

      // Send message based on channel
      let result: IMessageResult;
      switch (message.channel) {
        case MessageChannel.EMAIL:
          result = await this.sendEmail(message);
          break;
        case MessageChannel.SMS:
          result = await this.sendSms(message);
          break;
        case MessageChannel.PUSH:
          result = await this.sendPush(message);
          break;
        default:
          throw new Error(`Unsupported channel: ${message.channel}`);
      }

      // Log successful delivery
      this.logger.info('Message sent successfully', {
        messageId: message.id,
        channel: message.channel,
        recipient: message.recipient
      });

      return result;
    } catch (error) {
      this.logger.error('Failed to send message', {
        messageId: message.id,
        channel: message.channel,
        error: error instanceof Error ? error.message : String(error)
      });

      return this.createFailedResult(
        message.id,
        error instanceof Error ? error.message : 'Unknown error'
      );
    }
  }

  /**
   * Validates a message before sending
   * @param message - The message to validate
   * @throws Error if the message is invalid
   */
  private validateMessage(message: IMessage): void {
    if (!message.id) {
      throw new Error('Message ID is required');
    }

    if (!message.channel) {
      throw new Error('Message channel is required');
    }

    if (!message.recipient) {
      throw new Error('Message recipient is required');
    }

    if (!message.payload) {
      throw new Error('Message payload is required');
    }

    // Channel-specific validation
    switch (message.channel) {
      case MessageChannel.EMAIL:
        if (!message.payload.subject) {
          throw new Error('Email subject is required');
        }
        if (!message.payload.body && !message.payload.htmlBody) {
          throw new Error('Email body or HTML body is required');
        }
        // Validate email format
        if (!isValidEmail(message.recipient)) {
          throw new Error('Invalid email recipient format');
        }
        break;

      case MessageChannel.SMS:
        if (!message.payload.body) {
          throw new Error('SMS body is required');
        }
        // Validate phone number format
        if (!isValidPhoneNumber(message.recipient)) {
          throw new Error('Invalid phone number format');
        }
        break;

      case MessageChannel.PUSH:
        if (!message.payload.title) {
          throw new Error('Push notification title is required');
        }
        if (!message.payload.body) {
          throw new Error('Push notification body is required');
        }
        break;
    }
  }

  /**
   * Checks if the current rate limit for a channel has been exceeded
   * @param channel - The message channel to check
   * @returns true if the rate limit is not exceeded, false otherwise
   */
  private checkRateLimit(channel: MessageChannel): boolean {
    if (!this.config.rateLimits) {
      return true; // No rate limits configured
    }

    const limit = this.config.rateLimits[channel.toLowerCase() as keyof typeof this.config.rateLimits];
    if (!limit) {
      return true; // No rate limit for this channel
    }

    const now = new Date();
    const key = channel.toLowerCase();
    const counter = this.rateLimitCounters.get(key) || { count: 0, resetAt: new Date(now.getTime() + 60000) };

    // Reset counter if the minute has passed
    if (now >= counter.resetAt) {
      counter.count = 0;
      counter.resetAt = new Date(now.getTime() + 60000);
    }

    // Check if limit is exceeded
    if (counter.count >= limit) {
      this.logger.warn(`Rate limit exceeded for channel: ${channel}`, {
        channel,
        limit,
        count: counter.count,
        resetAt: counter.resetAt
      });
      return false;
    }

    // Increment counter
    counter.count++;
    this.rateLimitCounters.set(key, counter);
    return true;
  }

  /**
   * Processes a message template, replacing variables with values
   * @param message - The message with a templateId
   * @returns The processed message with template content
   */
  private async processTemplate(message: IMessage): Promise<IMessage> {
    try {
      const template = this.templates.get(message.templateId!);
      if (!template) {
        throw new Error(`Template not found: ${message.templateId}`);
      }

      // Check if template is for the correct channel
      if (template.channel !== message.channel) {
        throw new Error(`Template channel mismatch: expected ${message.channel}, got ${template.channel}`);
      }

      // Clone the message to avoid modifying the original
      const processedMessage = { ...message };
      
      // Apply template content
      if (template.subject) {
        processedMessage.payload.subject = this.replaceVariables(template.subject, message.payload.variables || {});
      }
      
      processedMessage.payload.body = this.replaceVariables(template.body, message.payload.variables || {});

      return processedMessage;
    } catch (error) {
      this.logger.error('Failed to process template', {
        templateId: message.templateId,
        error: error instanceof Error ? error.message : String(error)
      });
      throw error;
    }
  }

  /**
   * Replaces template variables with their values
   * @param content - The template content with placeholders
   * @param variables - The variables to replace in the template
   * @returns The content with variables replaced
   */
  private replaceVariables(content: string, variables: Record<string, any>): string {
    return content.replace(/\{\{([^}]+)\}\}/g, (match, variable) => {
      const value = variables[variable.trim()];
      return value !== undefined ? String(value) : match;
    });
  }

  /**
   * Sends an email message
   * @param message - The email message to send
   * @returns A promise that resolves to the message result
   */
  private async sendEmail(message: IMessage): Promise<IMessageResult> {
    if (!this.emailTransporter) {
      throw new Error('Email transporter not initialized');
    }

    try {
      const mailOptions = {
        from: message.sender || this.config.email?.from,
        to: message.recipient,
        subject: message.payload.subject,
        text: message.payload.body,
        html: message.payload.htmlBody,
        attachments: message.payload.attachments?.map(attachment => ({
          filename: attachment.name,
          contentType: attachment.contentType,
          content: attachment.content
        }))
      };

      const info = await this.emailTransporter.sendMail(mailOptions);

      return {
        messageId: message.id,
        success: true,
        status: MessageStatus.SENT,
        timestamp: new Date(),
        providerMessageId: info.messageId,
        providerResponse: JSON.stringify(info),
        deliveryMetrics: {
          latency: 0, // Would be calculated in a real implementation
          size: Buffer.byteLength(JSON.stringify(mailOptions), 'utf8')
        }
      };
    } catch (error) {
      this.logger.error('Failed to send email', {
        recipient: message.recipient,
        error: error instanceof Error ? error.message : String(error)
      });

      return this.createFailedResult(
        message.id,
        error instanceof Error ? error.message : 'Unknown error sending email'
      );
    }
  }

  /**
   * Sends an SMS message
   * @param message - The SMS message to send
   * @returns A promise that resolves to the message result
   */
  private async sendSms(message: IMessage): Promise<IMessageResult> {
    if (!this.config.sms) {
      throw new Error('SMS provider not configured');
    }

    try {
      // This is a simplified implementation that would be replaced with actual SMS provider integration
      // For example, using Twilio, Plivo, or another SMS service
      
      // Example of how this might be implemented with an HTTP API
      const response = await axios.post(`https://api.${this.config.sms.provider}.com/messages`, {
        from: message.sender || this.config.sms.from,
        to: message.recipient,
        body: message.payload.body
      }, {
        headers: {
          'Authorization': `Bearer ${this.config.sms.apiKey}`,
          'Content-Type': 'application/json'
        }
      });

      return {
        messageId: message.id,
        success: true,
        status: MessageStatus.SENT,
        timestamp: new Date(),
        providerMessageId: response.data.id,
        providerResponse: JSON.stringify(response.data),
        deliveryMetrics: {
          latency: 0, // Would be calculated in a real implementation
          size: Buffer.byteLength(message.payload.body || '', 'utf8'),
          cost: response.data.cost // Some providers return cost information
        }
      };
    } catch (error) {
      this.logger.error('Failed to send SMS', {
        recipient: message.recipient,
        error: error instanceof Error ? error.message : String(error)
      });

      return this.createFailedResult(
        message.id,
        error instanceof Error ? error.message : 'Unknown error sending SMS'
      );
    }
  }

  /**
   * Sends a push notification
   * @param message - The push notification message to send
   * @returns A promise that resolves to the message result
   */
  private async sendPush(message: IMessage): Promise<IMessageResult> {
    if (!this.config.push) {
      throw new Error('Push notification provider not configured');
    }

    try {
      // This is a simplified implementation that would be replaced with actual push provider integration
      // For example, using Firebase Cloud Messaging, OneSignal, or another push service
      
      // Example of how this might be implemented with an HTTP API
      const payload = {
        to: message.recipient, // Device token or registration ID
        notification: {
          title: message.payload.title,
          body: message.payload.body,
          icon: message.payload.imageUrl,
          click_action: message.payload.deepLink
        },
        data: message.payload.payload // Additional data to send with the notification
      };

      const response = await axios.post(`https://api.${this.config.push.provider}.com/send`, payload, {
        headers: {
          'Authorization': `key=${this.config.push.apiKey}`,
          'Content-Type': 'application/json'
        }
      });

      return {
        messageId: message.id,
        success: true,
        status: MessageStatus.SENT,
        timestamp: new Date(),
        providerMessageId: response.data.id,
        providerResponse: JSON.stringify(response.data),
        deliveryMetrics: {
          latency: 0, // Would be calculated in a real implementation
          size: Buffer.byteLength(JSON.stringify(payload), 'utf8')
        }
      };
    } catch (error) {
      this.logger.error('Failed to send push notification', {
        recipient: message.recipient,
        error: error instanceof Error ? error.message : String(error)
      });

      return this.createFailedResult(
        message.id,
        error instanceof Error ? error.message : 'Unknown error sending push notification'
      );
    }
  }

  /**
   * Creates a failed message result
   * @param messageId - The ID of the failed message
   * @param errorMessage - The error message
   * @returns A message result indicating failure
   */
  private createFailedResult(messageId: string, errorMessage: string): IMessageResult {
    return {
      messageId,
      success: false,
      status: MessageStatus.FAILED,
      timestamp: new Date(),
      errorCode: 'DELIVERY_FAILED',
      errorMessage,
      retryable: true // Most errors are retryable by default
    };
  }

  /**
   * Updates the delivery status of a message
   * @param messageId - The ID of the message to update
   * @param status - The new status of the message
   * @param details - Additional details about the status update
   * @returns A promise that resolves when the status is updated
   */
  public async updateMessageStatus(
    messageId: string,
    status: MessageStatus,
    details?: {
      providerMessageId?: string;
      deliveredAt?: Date;
      failedAt?: Date;
      errorDetails?: string;
    }
  ): Promise<void> {
    try {
      // In a real implementation, this would update the message status in a database
      // For now, we'll just log the status update
      this.logger.info('Message status updated', {
        messageId,
        status,
        ...details
      });
    } catch (error) {
      this.logger.error('Failed to update message status', {
        messageId,
        status,
        error: error instanceof Error ? error.message : String(error)
      });
      throw error;
    }
  }

  /**
   * Gets message delivery statistics for a time period
   * @param startDate - The start date for the statistics
   * @param endDate - The end date for the statistics
   * @param channel - Optional channel to filter by
   * @returns A promise that resolves to the message statistics
   */
  public async getMessageStats(
    startDate: Date,
    endDate: Date,
    channel?: MessageChannel
  ): Promise<{
    total: number;
    sent: number;
    delivered: number;
    failed: number;
    byChannel?: Record<MessageChannel, number>;
  }> {
    try {
      // In a real implementation, this would query a database for message statistics
      // For now, we'll just return mock statistics
      return {
        total: 0,
        sent: 0,
        delivered: 0,
        failed: 0,
        byChannel: channel ? undefined : {
          [MessageChannel.EMAIL]: 0,
          [MessageChannel.SMS]: 0,
          [MessageChannel.PUSH]: 0,
          [MessageChannel.WEBHOOK]: 0
        }
      };
    } catch (error) {
      this.logger.error('Failed to get message statistics', {
        startDate,
        endDate,
        channel,
        error: error instanceof Error ? error.message : String(error)
      });
      throw error;
    }
  }
}