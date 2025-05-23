import { createHash } from 'crypto';
import { Logger } from 'winston';
import { Redis } from 'ioredis';

import { config } from '../config';
import {
  INotification,
  INotificationResult,
  NotificationChannel,
  NotificationStatus,
  NotificationType,
  IDateValue,
  ILogContext,
} from '../types';
import { formatTime } from '../utils';

/**
 * Enum representing the types of audit events that can be logged.
 */
export enum AuditEventType {
  NOTIFICATION_CREATED = 'NOTIFICATION_CREATED',
  NOTIFICATION_DELIVERED = 'NOTIFICATION_DELIVERED',
  NOTIFICATION_FAILED = 'NOTIFICATION_FAILED',
  NOTIFICATION_RETRYING = 'NOTIFICATION_RETRYING',
  WEBHOOK_REQUEST_SENT = 'WEBHOOK_REQUEST_SENT',
  WEBHOOK_RESPONSE_RECEIVED = 'WEBHOOK_RESPONSE_RECEIVED',
  EMAIL_SENT = 'EMAIL_SENT',
  SMS_SENT = 'SMS_SENT',
  PUSH_SENT = 'PUSH_SENT',
  RETRY_SCHEDULED = 'RETRY_SCHEDULED',
  RETRY_ATTEMPTED = 'RETRY_ATTEMPTED',
  RETRY_EXHAUSTED = 'RETRY_EXHAUSTED',
  CONFIGURATION_CHANGED = 'CONFIGURATION_CHANGED',
  SECURITY_EVENT = 'SECURITY_EVENT',
  SYSTEM_ERROR = 'SYSTEM_ERROR'
}

/**
 * Interface for audit record data structure.
 * Captures comprehensive information about notification activities for compliance and troubleshooting.
 */
export interface IAuditRecord {
  /** Unique identifier for the audit record */
  id: string;
  /** Type of audit event */
  eventType: AuditEventType;
  /** Timestamp when the event occurred */
  timestamp: IDateValue;
  /** Associated notification ID if applicable */
  notificationId?: string;
  /** Associated recipient ID if applicable */
  recipientId?: string;
  /** Notification type if applicable */
  notificationType?: NotificationType;
  /** Notification channel if applicable */
  channel?: NotificationChannel;
  /** Current status of the notification */
  status?: NotificationStatus;
  /** User or system that initiated the action */
  actor: string;
  /** IP address where the action originated */
  sourceIp?: string;
  /** HTTP status code for webhook responses */
  statusCode?: number;
  /** Error message if applicable */
  errorMessage?: string;
  /** Duration of the operation in milliseconds */
  duration?: number;
  /** Number of retry attempts if applicable */
  retryCount?: number;
  /** Correlation ID for cross-service tracing */
  correlationId: string;
  /** Additional context-specific data */
  metadata?: Record<string, any>;
}

/**
 * Interface for audit record query parameters.
 * Used to filter audit records for reporting and compliance purposes.
 */
export interface IAuditQueryParams {
  /** Filter by event type */
  eventType?: AuditEventType | AuditEventType[];
  /** Filter by notification ID */
  notificationId?: string;
  /** Filter by recipient ID */
  recipientId?: string;
  /** Filter by notification type */
  notificationType?: NotificationType;
  /** Filter by notification channel */
  channel?: NotificationChannel;
  /** Filter by notification status */
  status?: NotificationStatus;
  /** Filter by actor (user or system) */
  actor?: string;
  /** Filter by start timestamp */
  startTime?: IDateValue;
  /** Filter by end timestamp */
  endTime?: IDateValue;
  /** Filter by correlation ID */
  correlationId?: string;
  /** Pagination: number of records to skip */
  skip?: number;
  /** Pagination: number of records to return */
  limit?: number;
  /** Sorting field */
  sortBy?: keyof IAuditRecord;
  /** Sorting direction */
  sortDirection?: 'asc' | 'desc';
}

/**
 * Interface for audit record storage options.
 * Configures how audit records are stored and retained.
 */
export interface IAuditStorageOptions {
  /** Whether to store audit records in the database */
  persistToDatabase: boolean;
  /** Whether to store audit records in Redis cache */
  cacheInRedis: boolean;
  /** TTL for Redis cache entries in seconds */
  redisTTL: number;
  /** Whether to include sensitive data in audit records */
  includeSensitiveData: boolean;
  /** Whether to compress audit records for storage */
  compressRecords: boolean;
}

/**
 * Interface for audit service configuration.
 */
export interface IAuditServiceConfig {
  /** Whether the audit service is enabled */
  enabled: boolean;
  /** Default storage options */
  storageOptions: IAuditStorageOptions;
  /** Events that should be excluded from auditing */
  excludedEvents?: AuditEventType[];
  /** Maximum size of metadata to store (in bytes) */
  maxMetadataSize: number;
  /** Whether to redact sensitive information */
  redactSensitiveInfo: boolean;
  /** Fields to consider sensitive */
  sensitiveFields: string[];
}

/**
 * Service that logs and stores audit records for all notification activities.
 * Captures detailed information about notification attempts, delivery status, and error conditions
 * for compliance, troubleshooting, and monitoring purposes.
 */
export class AuditService {
  private readonly logger: Logger;
  private readonly redis?: Redis;
  private readonly config: IAuditServiceConfig;
  private readonly defaultStorageOptions: IAuditStorageOptions;

  /**
   * Creates a new instance of the AuditService.
   * 
   * @param logger Winston logger instance for logging
   * @param redis Optional Redis client for caching audit records
   */
  constructor(logger: Logger, redis?: Redis) {
    this.logger = logger;
    this.redis = redis;
    
    // Load configuration from environment or defaults
    this.config = {
      enabled: config.audit?.enabled ?? true,
      storageOptions: {
        persistToDatabase: config.audit?.persistToDatabase ?? true,
        cacheInRedis: config.audit?.cacheInRedis ?? !!redis,
        redisTTL: config.audit?.redisTTL ?? 86400, // 24 hours default
        includeSensitiveData: config.audit?.includeSensitiveData ?? false,
        compressRecords: config.audit?.compressRecords ?? false,
      },
      excludedEvents: config.audit?.excludedEvents ?? [],
      maxMetadataSize: config.audit?.maxMetadataSize ?? 10240, // 10KB default
      redactSensitiveInfo: config.audit?.redactSensitiveInfo ?? true,
      sensitiveFields: config.audit?.sensitiveFields ?? [
        'password', 'token', 'secret', 'key', 'authorization', 'credential'
      ],
    };
    
    this.defaultStorageOptions = this.config.storageOptions;
    
    this.logger.info('AuditService initialized', { 
      enabled: this.config.enabled,
      persistToDatabase: this.defaultStorageOptions.persistToDatabase,
      cacheInRedis: this.defaultStorageOptions.cacheInRedis,
    });
  }

  /**
   * Creates and stores an audit record for a notification event.
   * 
   * @param eventType Type of audit event
   * @param data Additional data for the audit record
   * @param options Storage options for this specific audit record
   * @returns The created audit record ID
   */
  public async createAuditRecord(
    eventType: AuditEventType,
    data: Partial<IAuditRecord>,
    options?: Partial<IAuditStorageOptions>
  ): Promise<string> {
    try {
      // Skip if auditing is disabled or this event type is excluded
      if (!this.config.enabled || this.config.excludedEvents?.includes(eventType)) {
        return '';
      }

      const timestamp = formatTime(new Date());
      const id = this.generateAuditId(eventType, timestamp, data.correlationId || '');
      
      // Create the audit record
      const auditRecord: IAuditRecord = {
        id,
        eventType,
        timestamp,
        actor: data.actor || 'system',
        correlationId: data.correlationId || 'unknown',
        ...data,
      };

      // Process sensitive data if needed
      const processedRecord = this.config.redactSensitiveInfo 
        ? this.redactSensitiveData(auditRecord) 
        : auditRecord;
      
      // Trim metadata if it exceeds the maximum size
      if (processedRecord.metadata && 
          JSON.stringify(processedRecord.metadata).length > this.config.maxMetadataSize) {
        processedRecord.metadata = {
          _truncated: true,
          _originalSize: JSON.stringify(processedRecord.metadata).length,
          _message: 'Metadata exceeded maximum size and was truncated',
        };
      }

      // Determine storage options by merging defaults with provided options
      const storageOptions: IAuditStorageOptions = {
        ...this.defaultStorageOptions,
        ...options,
      };

      // Store the audit record based on configuration
      await this.storeAuditRecord(processedRecord, storageOptions);

      // Log the audit event at the appropriate level
      this.logAuditEvent(processedRecord);

      return id;
    } catch (error) {
      // Log the error but don't throw to avoid disrupting the main flow
      this.logger.error('Failed to create audit record', {
        eventType,
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
      });
      
      return '';
    }
  }

  /**
   * Logs a notification creation event.
   * 
   * @param notification The notification that was created
   * @param context Additional context information
   * @returns The created audit record ID
   */
  public async logNotificationCreated(
    notification: INotification,
    context: ILogContext
  ): Promise<string> {
    return this.createAuditRecord(AuditEventType.NOTIFICATION_CREATED, {
      notificationId: notification.id,
      notificationType: notification.type,
      status: notification.status,
      correlationId: context.correlationId,
      actor: context.userId || 'system',
      metadata: {
        recipientCount: notification.recipients.length,
        priority: notification.priority,
        channels: notification.recipients.map(r => r.channel),
      },
    });
  }

  /**
   * Logs a notification delivery event.
   * 
   * @param result The notification delivery result
   * @param context Additional context information
   * @returns The created audit record ID
   */
  public async logNotificationDelivered(
    result: INotificationResult,
    notification: INotification,
    context: ILogContext
  ): Promise<string> {
    const recipient = notification.recipients.find(r => r.id === result.recipientId);
    
    return this.createAuditRecord(AuditEventType.NOTIFICATION_DELIVERED, {
      notificationId: result.notificationId,
      recipientId: result.recipientId,
      notificationType: notification.type,
      channel: recipient?.channel,
      status: NotificationStatus.DELIVERED,
      statusCode: result.statusCode,
      duration: result.duration,
      correlationId: context.correlationId,
      actor: context.userId || 'system',
      metadata: {
        responseBody: result.responseBody ? this.truncateResponseBody(result.responseBody) : undefined,
        attemptedAt: result.attemptedAt,
      },
    });
  }

  /**
   * Logs a notification failure event.
   * 
   * @param result The notification delivery result
   * @param notification The notification that failed
   * @param context Additional context information
   * @returns The created audit record ID
   */
  public async logNotificationFailed(
    result: INotificationResult,
    notification: INotification,
    context: ILogContext
  ): Promise<string> {
    const recipient = notification.recipients.find(r => r.id === result.recipientId);
    
    return this.createAuditRecord(AuditEventType.NOTIFICATION_FAILED, {
      notificationId: result.notificationId,
      recipientId: result.recipientId,
      notificationType: notification.type,
      channel: recipient?.channel,
      status: NotificationStatus.FAILED,
      statusCode: result.statusCode,
      errorMessage: result.errorMessage,
      duration: result.duration,
      retryCount: notification.metadata.retryCount,
      correlationId: context.correlationId,
      actor: context.userId || 'system',
      metadata: {
        responseBody: result.responseBody ? this.truncateResponseBody(result.responseBody) : undefined,
        attemptedAt: result.attemptedAt,
        maxRetries: notification.metadata.maxRetries,
      },
    });
  }

  /**
   * Logs a notification retry event.
   * 
   * @param result The notification delivery result
   * @param notification The notification being retried
   * @param nextRetryAt When the next retry will be attempted
   * @param context Additional context information
   * @returns The created audit record ID
   */
  public async logNotificationRetrying(
    result: INotificationResult,
    notification: INotification,
    nextRetryAt: IDateValue,
    context: ILogContext
  ): Promise<string> {
    const recipient = notification.recipients.find(r => r.id === result.recipientId);
    
    return this.createAuditRecord(AuditEventType.NOTIFICATION_RETRYING, {
      notificationId: result.notificationId,
      recipientId: result.recipientId,
      notificationType: notification.type,
      channel: recipient?.channel,
      status: NotificationStatus.RETRYING,
      statusCode: result.statusCode,
      errorMessage: result.errorMessage,
      duration: result.duration,
      retryCount: notification.metadata.retryCount,
      correlationId: context.correlationId,
      actor: context.userId || 'system',
      metadata: {
        responseBody: result.responseBody ? this.truncateResponseBody(result.responseBody) : undefined,
        attemptedAt: result.attemptedAt,
        nextRetryAt,
        maxRetries: notification.metadata.maxRetries,
      },
    });
  }

  /**
   * Logs a webhook request event.
   * 
   * @param notificationId The notification ID
   * @param recipientId The recipient ID
   * @param url The webhook URL
   * @param context Additional context information
   * @returns The created audit record ID
   */
  public async logWebhookRequest(
    notificationId: string,
    recipientId: string,
    url: string,
    context: ILogContext
  ): Promise<string> {
    return this.createAuditRecord(AuditEventType.WEBHOOK_REQUEST_SENT, {
      notificationId,
      recipientId,
      channel: NotificationChannel.WEBHOOK,
      correlationId: context.correlationId,
      actor: context.userId || 'system',
      metadata: {
        url: this.redactUrlCredentials(url),
        timestamp: formatTime(new Date()),
      },
    });
  }

  /**
   * Logs a webhook response event.
   * 
   * @param notificationId The notification ID
   * @param recipientId The recipient ID
   * @param statusCode The HTTP status code
   * @param responseBody The response body
   * @param duration The request duration in milliseconds
   * @param context Additional context information
   * @returns The created audit record ID
   */
  public async logWebhookResponse(
    notificationId: string,
    recipientId: string,
    statusCode: number,
    responseBody: string,
    duration: number,
    context: ILogContext
  ): Promise<string> {
    return this.createAuditRecord(AuditEventType.WEBHOOK_RESPONSE_RECEIVED, {
      notificationId,
      recipientId,
      channel: NotificationChannel.WEBHOOK,
      statusCode,
      duration,
      correlationId: context.correlationId,
      actor: context.userId || 'system',
      metadata: {
        responseBody: this.truncateResponseBody(responseBody),
        timestamp: formatTime(new Date()),
      },
    });
  }

  /**
   * Logs a system error event.
   * 
   * @param error The error that occurred
   * @param context Additional context information
   * @returns The created audit record ID
   */
  public async logSystemError(
    error: Error,
    context: ILogContext,
    additionalData?: Record<string, any>
  ): Promise<string> {
    return this.createAuditRecord(AuditEventType.SYSTEM_ERROR, {
      errorMessage: error.message,
      correlationId: context.correlationId,
      actor: context.userId || 'system',
      metadata: {
        stack: error.stack,
        name: error.name,
        ...additionalData,
      },
    });
  }

  /**
   * Queries audit records based on the provided parameters.
   * 
   * @param params Query parameters to filter audit records
   * @returns Array of matching audit records
   */
  public async queryAuditRecords(params: IAuditQueryParams): Promise<IAuditRecord[]> {
    try {
      // This is a placeholder implementation
      // In a real implementation, this would query a database or other storage
      this.logger.info('Querying audit records', { params });
      
      // For now, just return an empty array
      // In a real implementation, this would return actual audit records
      return [];
    } catch (error) {
      this.logger.error('Failed to query audit records', {
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
      });
      
      return [];
    }
  }

  /**
   * Gets audit statistics for the specified time period.
   * 
   * @param startTime Start of the time period
   * @param endTime End of the time period
   * @returns Audit statistics
   */
  public async getAuditStats(
    startTime: IDateValue,
    endTime: IDateValue
  ): Promise<Record<string, any>> {
    try {
      // This is a placeholder implementation
      // In a real implementation, this would query a database or other storage
      this.logger.info('Getting audit statistics', { startTime, endTime });
      
      // For now, just return an empty object
      // In a real implementation, this would return actual statistics
      return {
        period: {
          start: startTime,
          end: endTime,
        },
        counts: {
          total: 0,
          byEventType: {},
          byStatus: {},
          byChannel: {},
        },
        performance: {
          averageDuration: 0,
          maxDuration: 0,
          p95Duration: 0,
        },
        errors: {
          count: 0,
          topErrors: [],
        },
      };
    } catch (error) {
      this.logger.error('Failed to get audit statistics', {
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
      });
      
      return {};
    }
  }

  /**
   * Exports audit records to a file or stream.
   * 
   * @param params Query parameters to filter audit records
   * @param format Export format (json, csv, etc.)
   * @returns Path to the exported file or stream
   */
  public async exportAuditRecords(
    params: IAuditQueryParams,
    format: 'json' | 'csv' = 'json'
  ): Promise<string> {
    try {
      // This is a placeholder implementation
      // In a real implementation, this would export audit records to a file or stream
      this.logger.info('Exporting audit records', { params, format });
      
      // For now, just return an empty string
      // In a real implementation, this would return the path to the exported file or stream
      return '';
    } catch (error) {
      this.logger.error('Failed to export audit records', {
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
      });
      
      return '';
    }
  }

  /**
   * Purges audit records older than the specified retention period.
   * 
   * @param retentionDays Number of days to retain audit records
   * @returns Number of purged records
   */
  public async purgeOldAuditRecords(retentionDays: number): Promise<number> {
    try {
      // This is a placeholder implementation
      // In a real implementation, this would purge old audit records from storage
      this.logger.info('Purging old audit records', { retentionDays });
      
      // For now, just return 0
      // In a real implementation, this would return the number of purged records
      return 0;
    } catch (error) {
      this.logger.error('Failed to purge old audit records', {
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
      });
      
      return 0;
    }
  }

  /**
   * Generates a unique ID for an audit record.
   * 
   * @param eventType Type of audit event
   * @param timestamp Timestamp of the event
   * @param correlationId Correlation ID for cross-service tracing
   * @returns Unique audit record ID
   */
  private generateAuditId(eventType: AuditEventType, timestamp: IDateValue, correlationId: string): string {
    const hash = createHash('sha256')
      .update(`${eventType}-${timestamp}-${correlationId}-${Date.now()}-${Math.random()}`)
      .digest('hex');
    
    return hash.substring(0, 24); // Return first 24 characters of the hash
  }

  /**
   * Stores an audit record based on the provided storage options.
   * 
   * @param record The audit record to store
   * @param options Storage options for this specific audit record
   */
  private async storeAuditRecord(
    record: IAuditRecord,
    options: IAuditStorageOptions
  ): Promise<void> {
    try {
      // Store in Redis cache if enabled
      if (options.cacheInRedis && this.redis) {
        const key = `audit:${record.id}`;
        await this.redis.set(
          key,
          JSON.stringify(record),
          'EX',
          options.redisTTL
        );
      }

      // Persist to database if enabled
      if (options.persistToDatabase) {
        // This is a placeholder for database persistence
        // In a real implementation, this would store the record in a database
        this.logger.debug('Would persist audit record to database', { recordId: record.id });
      }
    } catch (error) {
      this.logger.error('Failed to store audit record', {
        recordId: record.id,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  /**
   * Logs an audit event at the appropriate log level.
   * 
   * @param record The audit record to log
   */
  private logAuditEvent(record: IAuditRecord): void {
    // Determine the appropriate log level based on the event type
    let logLevel: 'error' | 'warn' | 'info' | 'debug' = 'info';
    
    if (record.eventType === AuditEventType.SYSTEM_ERROR) {
      logLevel = 'error';
    } else if (
      record.eventType === AuditEventType.NOTIFICATION_FAILED ||
      record.eventType === AuditEventType.RETRY_EXHAUSTED ||
      record.eventType === AuditEventType.SECURITY_EVENT
    ) {
      logLevel = 'warn';
    } else if (
      record.eventType === AuditEventType.CONFIGURATION_CHANGED
    ) {
      logLevel = 'debug';
    }

    // Log the audit event
    this.logger[logLevel]('Audit event', {
      eventType: record.eventType,
      notificationId: record.notificationId,
      status: record.status,
      correlationId: record.correlationId,
    });
  }

  /**
   * Redacts sensitive data from an audit record.
   * 
   * @param record The audit record to process
   * @returns The processed audit record with sensitive data redacted
   */
  private redactSensitiveData(record: IAuditRecord): IAuditRecord {
    // Create a deep copy of the record to avoid modifying the original
    const processedRecord = JSON.parse(JSON.stringify(record)) as IAuditRecord;
    
    // Process metadata if present
    if (processedRecord.metadata) {
      processedRecord.metadata = this.redactSensitiveFields(processedRecord.metadata);
    }
    
    return processedRecord;
  }

  /**
   * Redacts sensitive fields from an object.
   * 
   * @param obj The object to process
   * @returns The processed object with sensitive fields redacted
   */
  private redactSensitiveFields(obj: Record<string, any>): Record<string, any> {
    const result: Record<string, any> = {};
    
    for (const [key, value] of Object.entries(obj)) {
      // Check if this is a sensitive field
      const isSensitive = this.config.sensitiveFields.some(field => 
        key.toLowerCase().includes(field.toLowerCase())
      );
      
      if (isSensitive) {
        // Redact sensitive field
        result[key] = '[REDACTED]';
      } else if (typeof value === 'object' && value !== null) {
        // Recursively process nested objects
        result[key] = Array.isArray(value)
          ? value.map(item => typeof item === 'object' && item !== null ? this.redactSensitiveFields(item) : item)
          : this.redactSensitiveFields(value);
      } else {
        // Keep non-sensitive field as is
        result[key] = value;
      }
    }
    
    return result;
  }

  /**
   * Redacts credentials from a URL.
   * 
   * @param url The URL to process
   * @returns The URL with credentials redacted
   */
  private redactUrlCredentials(url: string): string {
    try {
      const urlObj = new URL(url);
      
      // Check if URL contains credentials
      if (urlObj.username || urlObj.password) {
        // Redact credentials
        urlObj.username = urlObj.username ? '[REDACTED]' : '';
        urlObj.password = urlObj.password ? '[REDACTED]' : '';
      }
      
      return urlObj.toString();
    } catch (error) {
      // If URL parsing fails, return the original URL
      return url;
    }
  }

  /**
   * Truncates a response body to a reasonable size for logging.
   * 
   * @param body The response body to truncate
   * @returns The truncated response body
   */
  private truncateResponseBody(body: string): string {
    const maxLength = 1000; // Maximum length for response bodies
    
    if (body.length <= maxLength) {
      return body;
    }
    
    return `${body.substring(0, maxLength)}... [truncated ${body.length - maxLength} characters]`;
  }
}

export default AuditService;