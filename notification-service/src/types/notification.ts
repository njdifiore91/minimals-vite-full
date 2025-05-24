import type { IDateValue } from './common';

// ----------------------------------------------------------------------

/**
 * Enum representing the types of notifications that can be sent.
 * Used to categorize notifications for processing and delivery.
 */
export enum NotificationType {
  STATUS_UPDATE = 'STATUS_UPDATE', // Application status changes
  ERROR = 'ERROR',                // System or processing errors
  COMPLETION = 'COMPLETION'       // Application processing completion
}

/**
 * Enum representing the current status of a notification delivery.
 * Used to track the delivery lifecycle of notifications.
 */
export enum NotificationStatus {
  PENDING = 'PENDING',     // Initial state, not yet delivered
  DELIVERED = 'DELIVERED', // Successfully delivered to recipient
  FAILED = 'FAILED',       // Delivery failed and will not be retried
  RETRYING = 'RETRYING'    // Delivery failed but will be retried
}

/**
 * Enum representing the priority levels for notifications.
 * Used to determine processing order and delivery urgency.
 */
export enum NotificationPriority {
  LOW = 'LOW',           // Non-urgent, can be delayed if necessary
  MEDIUM = 'MEDIUM',     // Standard priority
  HIGH = 'HIGH',         // Urgent, should be processed quickly
  CRITICAL = 'CRITICAL'  // Highest priority, process immediately
}

/**
 * Enum representing the available notification delivery channels.
 * Used to determine how a notification should be delivered.
 */
export enum NotificationChannel {
  WEBHOOK = 'WEBHOOK', // Deliver via HTTP webhook
  EMAIL = 'EMAIL',     // Deliver via email
  SMS = 'SMS',         // Deliver via SMS
  PUSH = 'PUSH'        // Deliver via push notification
}

/**
 * Interface for notification recipient information.
 * Contains the channel type and contact details for delivery.
 */
export interface INotificationRecipient {
  id: string;                        // Unique identifier for the recipient
  name?: string;                     // Optional name of the recipient
  channel: NotificationChannel;      // Delivery channel for this recipient
  destination: string;               // Channel-specific destination (URL, email, phone, etc.)
  active: boolean;                   // Whether this recipient is currently active
  metadata?: Record<string, any>;    // Additional recipient-specific metadata
  createdAt: IDateValue;             // When this recipient was created
  updatedAt: IDateValue;             // When this recipient was last updated
}

/**
 * Interface for structured notification content.
 * Defines the actual content to be delivered to recipients.
 */
export interface INotificationPayload {
  title: string;                     // Title or subject of the notification
  body: string;                      // Main content of the notification
  data: Record<string, any>;         // Structured data associated with the notification
  templateId?: string;               // Optional template identifier for formatted notifications
  templateData?: Record<string, any>; // Data to be used with the template
}

/**
 * Interface for additional notification context.
 * Contains metadata about the notification for tracking and auditing.
 */
export interface INotificationMetadata {
  applicationId?: string;            // Associated application ID if relevant
  documentId?: string;               // Associated document ID if relevant
  userId?: string;                   // User who triggered the notification if relevant
  correlationId: string;             // Unique ID for tracking related operations
  source: string;                    // System component that generated the notification
  tags: string[];                    // Categorization tags for filtering and reporting
  retryCount?: number;               // Number of delivery attempts if retrying
  maxRetries?: number;               // Maximum number of retry attempts allowed
  nextRetryAt?: IDateValue;          // When to attempt the next retry if applicable
}

/**
 * Comprehensive interface for a notification.
 * Combines all notification components into a complete model.
 */
export interface INotification {
  id: string;                        // Unique identifier for the notification
  type: NotificationType;            // Type of notification
  status: NotificationStatus;        // Current delivery status
  priority: NotificationPriority;    // Priority level
  recipients: INotificationRecipient[]; // List of recipients
  payload: INotificationPayload;     // Content to be delivered
  metadata: INotificationMetadata;   // Additional context
  createdAt: IDateValue;             // When the notification was created
  updatedAt: IDateValue;             // When the notification was last updated
  deliveredAt?: IDateValue;          // When the notification was successfully delivered
}

/**
 * Interface for notification delivery attempt results.
 * Used to track the outcome of each delivery attempt.
 */
export interface INotificationResult {
  id: string;                        // Unique identifier for this result
  notificationId: string;            // Reference to the parent notification
  recipientId: string;               // Recipient this result applies to
  successful: boolean;               // Whether delivery was successful
  statusCode?: number;               // HTTP status code for webhook deliveries
  responseBody?: string;             // Response body from recipient if available
  errorMessage?: string;             // Error message if delivery failed
  attemptedAt: IDateValue;           // When this delivery attempt was made
  duration: number;                  // Time taken for delivery attempt in milliseconds
  metadata?: Record<string, any>;    // Additional result-specific metadata
}

/**
 * Interface for notification batch processing.
 * Used when sending multiple notifications as a group.
 */
export interface INotificationBatch {
  id: string;                        // Unique identifier for the batch
  notifications: INotification[];    // Notifications in this batch
  createdAt: IDateValue;             // When the batch was created
  completedAt?: IDateValue;          // When all notifications in the batch were processed
  status: NotificationStatus;        // Overall status of the batch
  metadata?: Record<string, any>;    // Additional batch-specific metadata
}

/**
 * Interface for notification delivery statistics.
 * Used for monitoring and reporting on notification processing.
 */
export interface INotificationStats {
  totalSent: number;                 // Total notifications sent
  totalDelivered: number;            // Successfully delivered notifications
  totalFailed: number;               // Failed notifications
  totalRetrying: number;             // Notifications in retry state
  averageDeliveryTime: number;       // Average delivery time in milliseconds
  deliverySuccessRate: number;       // Percentage of successful deliveries
  byType: Record<NotificationType, number>; // Count by notification type
  byChannel: Record<NotificationChannel, number>; // Count by delivery channel
  byPriority: Record<NotificationPriority, number>; // Count by priority level
}