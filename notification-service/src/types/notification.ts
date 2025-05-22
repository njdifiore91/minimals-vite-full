/**
 * Notification Types
 * 
 * This file defines TypeScript interfaces and types for the notification domain model.
 * It provides type definitions for notification types, statuses, priorities, recipients,
 * payloads, and delivery results to ensure type safety for all notification-related operations
 * and enable consistent handling of notifications across different channels.
 */

import type { IDateValue, IRetryOptions } from './common';
import type { MessageChannel } from './message';
import type { WebhookMethod } from './webhook';

// ----------------------------------------------------------------------

/**
 * Enum representing the types of notifications that can be sent.
 */
export enum NotificationType {
  /** Notification for application status changes */
  STATUS_UPDATE = 'status_update',
  /** Notification for errors in processing */
  ERROR = 'error',
  /** Notification for completed processes */
  COMPLETION = 'completion',
  /** Notification for document processing updates */
  DOCUMENT_UPDATE = 'document_update',
  /** Notification for new applications */
  NEW_APPLICATION = 'new_application',
  /** Notification for system alerts */
  SYSTEM_ALERT = 'system_alert'
}

/**
 * Enum representing the possible statuses of a notification in the delivery lifecycle.
 */
export enum NotificationStatus {
  /** Notification is created but not yet processed */
  CREATED = 'created',
  /** Notification is queued for delivery */
  PENDING = 'pending',
  /** Notification has been successfully delivered */
  DELIVERED = 'delivered',
  /** Notification delivery has failed */
  FAILED = 'failed',
  /** Notification is being retried after a failure */
  RETRYING = 'retrying',
  /** Notification has been cancelled */
  CANCELLED = 'cancelled'
}

/**
 * Enum representing the priority levels for notification delivery.
 */
export enum NotificationPriority {
  /** Low priority notifications */
  LOW = 'low',
  /** Medium priority notifications */
  MEDIUM = 'medium',
  /** High priority notifications */
  HIGH = 'high',
  /** Critical priority notifications that require immediate attention */
  CRITICAL = 'critical'
}

/**
 * Interface for notification recipient information.
 */
export interface INotificationRecipient {
  /** Unique identifier for the recipient */
  id: string;
  /** Type of recipient (user, system, webhook endpoint) */
  type: 'user' | 'system' | 'webhook' | 'external';
  /** Name of the recipient */
  name?: string;
  /** Email address for email notifications */
  email?: string;
  /** Phone number for SMS notifications */
  phone?: string;
  /** Device token for push notifications */
  deviceToken?: string;
  /** Webhook URL for webhook notifications */
  webhookUrl?: string;
  /** Webhook method for webhook notifications */
  webhookMethod?: WebhookMethod;
  /** Webhook headers for webhook notifications */
  webhookHeaders?: Record<string, string>;
  /** Webhook secret for signing payloads */
  webhookSecret?: string;
  /** Preferred notification channels in order of preference */
  preferredChannels?: MessageChannel[];
  /** Whether the recipient is active */
  isActive: boolean;
  /** Associated application ID */
  applicationId?: string;
  /** Associated merchant ID */
  merchantId?: string;
  /** Associated user ID */
  userId?: string;
  /** Role of the recipient */
  role?: string;
  /** Additional recipient metadata */
  metadata?: Record<string, any>;
}

/**
 * Interface for structured notification content.
 */
export interface INotificationPayload {
  /** Notification title */
  title: string;
  /** Notification message */
  message: string;
  /** Detailed notification content (HTML for email, JSON for webhooks) */
  content?: string;
  /** Action URL for clickable notifications */
  actionUrl?: string;
  /** Action text for clickable notifications */
  actionText?: string;
  /** Secondary action URL */
  secondaryActionUrl?: string;
  /** Secondary action text */
  secondaryActionText?: string;
  /** Image URL for rich notifications */
  imageUrl?: string;
  /** Icon URL for notifications with icons */
  iconUrl?: string;
  /** Template ID if using a template */
  templateId?: string;
  /** Template variables for dynamic content */
  templateVariables?: Record<string, any>;
  /** Data associated with the notification */
  data?: Record<string, any>;
  /** Whether the notification contains sensitive information */
  containsSensitiveInfo?: boolean;
  /** Expiration date for the notification */
  expiresAt?: IDateValue;
}

/**
 * Interface for additional notification context and metadata.
 */
export interface INotificationMetadata {
  /** Associated application ID */
  applicationId?: string;
  /** Associated document IDs */
  documentIds?: string[];
  /** Associated merchant ID */
  merchantId?: string;
  /** Associated user ID */
  userId?: string;
  /** Event that triggered the notification */
  triggerEvent?: string;
  /** Source service that generated the notification */
  sourceService?: string;
  /** Correlation ID for distributed tracing */
  correlationId?: string;
  /** Request ID that initiated the notification */
  requestId?: string;
  /** IP address of the request that triggered the notification */
  ipAddress?: string;
  /** User agent of the request that triggered the notification */
  userAgent?: string;
  /** Tags for categorizing notifications */
  tags?: string[];
  /** Environment the notification was generated in */
  environment?: string;
  /** Additional custom metadata */
  customData?: Record<string, any>;
}

/**
 * Interface for notification delivery options and settings.
 */
export interface INotificationDeliveryOptions {
  /** Notification priority */
  priority: NotificationPriority;
  /** Channels to deliver the notification through */
  channels: MessageChannel[];
  /** Whether to attempt delivery through all channels or stop after first success */
  deliverToAllChannels: boolean;
  /** Scheduled delivery time */
  scheduledAt?: IDateValue;
  /** Notification expiration time */
  expiresAt?: IDateValue;
  /** Retry options for failed deliveries */
  retry?: IRetryOptions;
  /** Whether to require delivery confirmation */
  requireConfirmation?: boolean;
  /** Idempotency key to prevent duplicate deliveries */
  idempotencyKey?: string;
  /** Whether to track notification opens/clicks */
  trackEngagement?: boolean;
  /** Whether to encrypt sensitive content */
  encryptContent?: boolean;
  /** Whether to sign the notification payload */
  signPayload?: boolean;
  /** Channel-specific delivery options */
  channelOptions?: {
    /** Email-specific options */
    email?: {
      /** CC recipients */
      cc?: string[];
      /** BCC recipients */
      bcc?: string[];
      /** Reply-to address */
      replyTo?: string;
      /** Email subject */
      subject?: string;
      /** Whether to send as HTML */
      isHtml?: boolean;
      /** Email attachments */
      attachments?: Array<{
        filename: string;
        content: string | Buffer;
        contentType: string;
      }>;
    };
    /** SMS-specific options */
    sms?: {
      /** SMS sender ID */
      senderId?: string;
      /** Whether to use Unicode */
      unicode?: boolean;
      /** Whether to flash the message on the recipient's screen */
      flash?: boolean;
    };
    /** Push notification-specific options */
    push?: {
      /** Badge count */
      badge?: number;
      /** Sound to play */
      sound?: string;
      /** Whether the notification is silent */
      silent?: boolean;
      /** Time to live in seconds */
      ttl?: number;
      /** Collapse key for grouping notifications */
      collapseKey?: string;
    };
    /** Webhook-specific options */
    webhook?: {
      /** HTTP method */
      method?: WebhookMethod;
      /** HTTP headers */
      headers?: Record<string, string>;
      /** Request timeout in milliseconds */
      timeoutMs?: number;
      /** Whether to verify SSL certificates */
      verifySSL?: boolean;
      /** Authentication type */
      authType?: 'none' | 'basic' | 'bearer' | 'custom';
      /** Authentication credentials */
      auth?: {
        /** Username for basic auth */
        username?: string;
        /** Password for basic auth */
        password?: string;
        /** Token for bearer auth */
        token?: string;
        /** Header name for custom auth */
        headerName?: string;
        /** Header value for custom auth */
        headerValue?: string;
      };
    };
  };
}

/**
 * Comprehensive interface for a notification in the system.
 */
export interface INotification {
  /** Unique identifier for the notification */
  id: string;
  /** Type of notification */
  type: NotificationType;
  /** Current status of the notification */
  status: NotificationStatus;
  /** Notification recipients */
  recipients: INotificationRecipient[];
  /** Notification content */
  payload: INotificationPayload;
  /** Additional notification context */
  metadata?: INotificationMetadata;
  /** Delivery options and settings */
  deliveryOptions: INotificationDeliveryOptions;
  /** Creation timestamp */
  createdAt: IDateValue;
  /** Last updated timestamp */
  updatedAt: IDateValue;
  /** Scheduled delivery timestamp */
  scheduledAt?: IDateValue;
  /** Delivery timestamp */
  deliveredAt?: IDateValue;
  /** Failure timestamp */
  failedAt?: IDateValue;
  /** Error details if delivery failed */
  errorDetails?: string;
  /** Current retry count */
  retryCount?: number;
  /** Next scheduled retry timestamp */
  nextRetryAt?: IDateValue;
  /** Delivery results for each channel */
  deliveryResults?: Record<MessageChannel, INotificationResult[]>;
  /** Whether the notification has been read by the recipient */
  isRead?: boolean;
  /** Timestamp when the notification was read */
  readAt?: IDateValue;
  /** Whether the notification has been clicked/actioned */
  isActioned?: boolean;
  /** Timestamp when the notification was clicked/actioned */
  actionedAt?: IDateValue;
}

/**
 * Interface for notification delivery attempt results.
 */
export interface INotificationResult {
  /** Unique identifier for the delivery attempt */
  id: string;
  /** Associated notification ID */
  notificationId: string;
  /** Recipient the notification was delivered to */
  recipientId: string;
  /** Channel used for delivery */
  channel: MessageChannel;
  /** Whether delivery was successful */
  success: boolean;
  /** Delivery status */
  status: NotificationStatus;
  /** Timestamp of the delivery attempt */
  timestamp: IDateValue;
  /** Provider-specific response */
  providerResponse?: string;
  /** Provider-specific message ID */
  providerMessageId?: string;
  /** Delivery performance metrics */
  metrics?: {
    /** Delivery latency in milliseconds */
    latencyMs?: number;
    /** Message size in bytes */
    sizeBytes?: number;
    /** Delivery cost (if applicable) */
    cost?: number;
  };
  /** Error code if delivery failed */
  errorCode?: string;
  /** Error message if delivery failed */
  errorMessage?: string;
  /** Whether the error is retryable */
  isRetryable?: boolean;
  /** Retry attempt number (0 for initial attempt) */
  retryAttempt?: number;
  /** Next scheduled retry timestamp */
  nextRetryAt?: IDateValue;
  /** IP address the notification was sent from */
  sourceIp?: string;
  /** Whether the notification was opened/viewed */
  isOpened?: boolean;
  /** Timestamp when the notification was opened/viewed */
  openedAt?: IDateValue;
  /** Whether the notification was clicked */
  isClicked?: boolean;
  /** Timestamp when the notification was clicked */
  clickedAt?: IDateValue;
  /** URL that was clicked (if applicable) */
  clickedUrl?: string;
  /** Device information of the recipient */
  deviceInfo?: {
    /** Device type */
    type?: string;
    /** Operating system */
    os?: string;
    /** Browser */
    browser?: string;
    /** IP address */
    ip?: string;
    /** User agent */
    userAgent?: string;
  };
}

/**
 * Interface for notification template used for generating standardized notifications.
 */
export interface INotificationTemplate {
  /** Unique identifier for the template */
  id: string;
  /** Template name */
  name: string;
  /** Template description */
  description?: string;
  /** Notification type this template is for */
  notificationType: NotificationType;
  /** Channels this template supports */
  supportedChannels: MessageChannel[];
  /** Template title with placeholders */
  title: string;
  /** Template message with placeholders */
  message: string;
  /** Template content with placeholders (HTML for email, JSON for webhooks) */
  content?: string;
  /** Action URL template with placeholders */
  actionUrl?: string;
  /** Action text */
  actionText?: string;
  /** Secondary action URL template with placeholders */
  secondaryActionUrl?: string;
  /** Secondary action text */
  secondaryActionText?: string;
  /** Image URL */
  imageUrl?: string;
  /** Icon URL */
  iconUrl?: string;
  /** Variables used in the template */
  variables: string[];
  /** Default variable values */
  defaultVariables?: Record<string, any>;
  /** Whether the template is active */
  isActive: boolean;
  /** Template version */
  version: number;
  /** Creation timestamp */
  createdAt: IDateValue;
  /** Last updated timestamp */
  updatedAt: IDateValue;
  /** User who created the template */
  createdBy?: string;
  /** User who last updated the template */
  updatedBy?: string;
  /** Channel-specific template variations */
  channelTemplates?: {
    /** Email-specific template */
    email?: {
      /** Email subject template */
      subject: string;
      /** Email HTML body template */
      htmlBody: string;
      /** Email text body template */
      textBody: string;
    };
    /** SMS-specific template */
    sms?: {
      /** SMS message template */
      message: string;
    };
    /** Push notification-specific template */
    push?: {
      /** Push notification title template */
      title: string;
      /** Push notification body template */
      body: string;
      /** Push notification data template */
      data?: Record<string, any>;
    };
    /** Webhook-specific template */
    webhook?: {
      /** Webhook payload template */
      payload: Record<string, any>;
    };
  };
}

/**
 * Interface for notification preferences for a recipient.
 */
export interface INotificationPreferences {
  /** Recipient ID */
  recipientId: string;
  /** Global opt-in/opt-out status */
  optedIn: boolean;
  /** Channel-specific preferences */
  channelPreferences: {
    /** Email notification preferences */
    email?: {
      /** Whether email notifications are enabled */
      enabled: boolean;
      /** Email address to use */
      address?: string;
      /** Format preference (html, text) */
      format?: 'html' | 'text';
    };
    /** SMS notification preferences */
    sms?: {
      /** Whether SMS notifications are enabled */
      enabled: boolean;
      /** Phone number to use */
      phoneNumber?: string;
    };
    /** Push notification preferences */
    push?: {
      /** Whether push notifications are enabled */
      enabled: boolean;
      /** Device tokens to use */
      deviceTokens?: string[];
    };
    /** Webhook notification preferences */
    webhook?: {
      /** Whether webhook notifications are enabled */
      enabled: boolean;
      /** Webhook endpoints to use */
      endpoints?: Array<{
        /** Webhook URL */
        url: string;
        /** Webhook method */
        method: WebhookMethod;
        /** Webhook headers */
        headers?: Record<string, string>;
        /** Webhook secret */
        secret?: string;
      }>;
    };
  };
  /** Notification type preferences */
  typePreferences: {
    /** Notification type */
    [key in NotificationType]?: {
      /** Whether this notification type is enabled */
      enabled: boolean;
      /** Channels to use for this notification type */
      channels?: MessageChannel[];
    };
  };
  /** Time-based preferences */
  timePreferences?: {
    /** Timezone for the recipient */
    timezone: string;
    /** Quiet hours start time (HH:MM) */
    quietHoursStart?: string;
    /** Quiet hours end time (HH:MM) */
    quietHoursEnd?: string;
    /** Days of week to receive notifications (0 = Sunday, 6 = Saturday) */
    activeDays?: number[];
  };
  /** Last updated timestamp */
  updatedAt: IDateValue;
}

/**
 * Interface for notification statistics and analytics.
 */
export interface INotificationStats {
  /** Time period for the statistics */
  period: {
    /** Start of the period */
    start: IDateValue;
    /** End of the period */
    end: IDateValue;
  };
  /** Total notifications sent */
  totalSent: number;
  /** Notifications by status */
  byStatus: {
    /** Created notifications */
    created: number;
    /** Pending notifications */
    pending: number;
    /** Delivered notifications */
    delivered: number;
    /** Failed notifications */
    failed: number;
    /** Retrying notifications */
    retrying: number;
    /** Cancelled notifications */
    cancelled: number;
  };
  /** Notifications by type */
  byType: {
    /** Status update notifications */
    statusUpdate: number;
    /** Error notifications */
    error: number;
    /** Completion notifications */
    completion: number;
    /** Document update notifications */
    documentUpdate: number;
    /** New application notifications */
    newApplication: number;
    /** System alert notifications */
    systemAlert: number;
  };
  /** Notifications by channel */
  byChannel: {
    /** Email notifications */
    email: number;
    /** SMS notifications */
    sms: number;
    /** Push notifications */
    push: number;
    /** Webhook notifications */
    webhook: number;
  };
  /** Delivery success rates by channel */
  successRates: {
    /** Overall success rate */
    overall: number;
    /** Email success rate */
    email: number;
    /** SMS success rate */
    sms: number;
    /** Push success rate */
    push: number;
    /** Webhook success rate */
    webhook: number;
  };
  /** Engagement metrics */
  engagement: {
    /** Open rate */
    openRate: number;
    /** Click rate */
    clickRate: number;
    /** Action completion rate */
    actionRate: number;
  };
  /** Performance metrics */
  performance: {
    /** Average delivery time in milliseconds */
    avgDeliveryTimeMs: number;
    /** 95th percentile delivery time in milliseconds */
    p95DeliveryTimeMs: number;
    /** Average retry count for failed notifications */
    avgRetryCount: number;
  };
}