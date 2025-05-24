import type { IDateValue } from './common';

// ----------------------------------------------------------------------

/**
 * Enum representing the available communication channels for message delivery.
 */
export enum MessageChannel {
  EMAIL = 'email',
  SMS = 'sms',
  PUSH = 'push',
  WEBHOOK = 'webhook'
}

/**
 * Enum representing the possible statuses of a message in the delivery lifecycle.
 */
export enum MessageStatus {
  QUEUED = 'queued',     // Message is queued for delivery
  SENT = 'sent',         // Message has been sent to the delivery provider
  DELIVERED = 'delivered', // Message has been confirmed as delivered
  FAILED = 'failed'      // Message delivery has failed
}

/**
 * Enum representing the priority levels for message delivery.
 */
export enum MessagePriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

/**
 * Interface for message templates used for generating standardized messages.
 */
export interface IMessageTemplate {
  id: string;
  name: string;
  description?: string;
  channel: MessageChannel;
  subject?: string;       // For email templates
  body: string;           // Template content with placeholders
  variables: string[];    // List of variables used in the template
  createdAt: IDateValue;
  updatedAt: IDateValue;
  version: number;        // Template version for tracking changes
  isActive: boolean;      // Whether the template is active
}

/**
 * Interface for channel-specific message content.
 */
export interface IMessagePayload {
  // Common fields
  body: string;           // Main message content
  variables?: Record<string, any>; // Variables to be interpolated in templates
  
  // Channel-specific fields
  subject?: string;       // For email messages
  htmlBody?: string;      // For email HTML content
  attachments?: Array<{
    name: string;
    contentType: string;
    content: string | Buffer;
    size: number;
  }>;
  
  // SMS-specific fields
  senderName?: string;    // For SMS sender ID
  
  // Push notification fields
  title?: string;         // For push notification title
  imageUrl?: string;      // For rich push notifications
  deepLink?: string;      // For mobile app deep linking
  
  // Webhook fields
  url?: string;           // For webhook destination
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'; // For webhook HTTP method
  headers?: Record<string, string>; // For webhook HTTP headers
  payload?: Record<string, any>;    // For webhook payload
}

/**
 * Interface for additional message context and metadata.
 */
export interface IMessageMetadata {
  applicationId?: string;  // Associated application ID
  userId?: string;        // Associated user ID
  merchantId?: string;    // Associated merchant ID
  documentIds?: string[]; // Associated document IDs
  eventType?: string;     // Type of event triggering the message
  correlationId?: string; // For tracking related messages
  ipAddress?: string;     // Sender IP address for security tracking
  userAgent?: string;     // User agent for device tracking
  tags?: string[];        // Tags for message categorization
  customData?: Record<string, any>; // Additional custom metadata
}

/**
 * Interface for channel-specific delivery settings and options.
 */
export interface IMessageDeliveryOptions {
  priority: MessagePriority;  // Message priority
  scheduled?: IDateValue;     // Scheduled delivery time
  expiration?: IDateValue;    // Message expiration time
  maxRetries?: number;        // Maximum delivery retry attempts
  retryInterval?: number;     // Interval between retries in milliseconds
  retryStrategy?: 'linear' | 'exponential'; // Retry backoff strategy
  requireConfirmation?: boolean; // Whether delivery confirmation is required
  idempotencyKey?: string;    // For preventing duplicate deliveries
  provider?: string;          // Specific provider to use for this channel
  providerOptions?: Record<string, any>; // Provider-specific options
  encryptContent?: boolean;   // Whether to encrypt message content
  signatureRequired?: boolean; // Whether to sign the message payload
}

/**
 * Comprehensive interface for a message in the notification system.
 */
export interface IMessage {
  id: string;                 // Unique message identifier
  channel: MessageChannel;    // Delivery channel
  status: MessageStatus;      // Current message status
  recipient: string;          // Recipient address (email, phone, device token, webhook URL)
  sender?: string;            // Sender identifier
  templateId?: string;        // Associated template ID if using a template
  payload: IMessagePayload;   // Message content
  metadata?: IMessageMetadata; // Additional message context
  deliveryOptions: IMessageDeliveryOptions; // Delivery settings
  createdAt: IDateValue;      // Message creation timestamp
  updatedAt: IDateValue;      // Last update timestamp
  sentAt?: IDateValue;        // When the message was sent
  deliveredAt?: IDateValue;   // When the message was delivered
  failedAt?: IDateValue;      // When the message failed (if applicable)
  errorDetails?: string;      // Error details if delivery failed
  retryCount?: number;        // Current retry count
  nextRetryAt?: IDateValue;   // Next scheduled retry time
}

/**
 * Interface for message delivery attempt results.
 */
export interface IMessageResult {
  messageId: string;          // Associated message ID
  success: boolean;           // Whether delivery was successful
  status: MessageStatus;      // Updated message status
  timestamp: IDateValue;      // Result timestamp
  providerResponse?: string;  // Raw provider response
  providerMessageId?: string; // Provider-specific message ID
  deliveryMetrics?: {         // Delivery performance metrics
    latency?: number;         // Delivery latency in milliseconds
    size?: number;            // Message size in bytes
    cost?: number;            // Delivery cost (if applicable)
  };
  errorCode?: string;         // Error code if delivery failed
  errorMessage?: string;      // Error message if delivery failed
  retryable?: boolean;        // Whether the error is retryable
}