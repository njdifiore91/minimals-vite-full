/**
 * Audit Service
 * 
 * This service logs and stores audit records for all notification activities.
 * It captures detailed information about notification attempts, delivery status,
 * and error conditions for compliance, troubleshooting, and monitoring purposes.
 */

import { v4 as uuidv4 } from 'uuid';
import { Logger } from 'winston';
import { Pool, PoolClient } from 'pg';

// Import types
import { 
  ILogContext, 
  IServiceStatus,
  IDateValue 
} from '../types/common';
import { 
  NotificationType, 
  NotificationStatus,
  NotificationPriority 
} from '../types/notification';
import { MessageChannel, MessageStatus } from '../types/message';
import { WebhookStatus } from '../types/webhook';

// Import configuration
import { logger } from '../config/logger';
import { appConfig } from '../config/app';

// Import utilities
import { formatTime } from '../utils/format-time';

/**
 * Enum representing the types of audit events
 */
export enum AuditEventType {
  // Notification events
  NOTIFICATION_RECEIVED = 'NOTIFICATION_RECEIVED',
  NOTIFICATION_PROCESSED = 'NOTIFICATION_PROCESSED',
  NOTIFICATION_COMPLETED = 'NOTIFICATION_COMPLETED',
  NOTIFICATION_FAILED = 'NOTIFICATION_FAILED',
  
  // Webhook events
  WEBHOOK_DELIVERY_ATTEMPTED = 'WEBHOOK_DELIVERY_ATTEMPTED',
  WEBHOOK_DELIVERY_SUCCEEDED = 'WEBHOOK_DELIVERY_SUCCEEDED',
  WEBHOOK_DELIVERY_FAILED = 'WEBHOOK_DELIVERY_FAILED',
  WEBHOOK_RESPONSE_RECEIVED = 'WEBHOOK_RESPONSE_RECEIVED',
  
  // Retry events
  RETRY_SCHEDULED = 'RETRY_SCHEDULED',
  RETRY_ATTEMPTED = 'RETRY_ATTEMPTED',
  RETRY_SUCCEEDED = 'RETRY_SUCCEEDED',
  RETRY_FAILED = 'RETRY_FAILED',
  RETRY_EXHAUSTED = 'RETRY_EXHAUSTED',
  
  // Message events
  MESSAGE_CREATED = 'MESSAGE_CREATED',
  MESSAGE_SENT = 'MESSAGE_SENT',
  MESSAGE_DELIVERED = 'MESSAGE_DELIVERED',
  MESSAGE_FAILED = 'MESSAGE_FAILED',
  
  // System events
  SYSTEM_ERROR = 'SYSTEM_ERROR',
  CONFIGURATION_CHANGED = 'CONFIGURATION_CHANGED',
  SERVICE_STARTED = 'SERVICE_STARTED',
  SERVICE_STOPPED = 'SERVICE_STOPPED'
}

/**
 * Enum representing the outcome status of audit events
 */
export enum AuditStatus {
  SUCCESS = 'SUCCESS',
  FAILURE = 'FAILURE',
  WARNING = 'WARNING',
  INFO = 'INFO'
}

/**
 * Interface representing an audit record
 */
export interface IAuditRecord {
  id: string;
  timestamp: Date;
  eventType: AuditEventType;
  status: AuditStatus;
  channel?: MessageChannel;
  recipientId?: string;
  notificationId?: string;
  messageId?: string;
  duration?: number;
  errorCode?: string;
  errorMessage?: string;
  metadata: Record<string, any>;
  correlationId: string;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Interface for audit record creation
 */
export interface IAuditRecordCreate {
  eventType: AuditEventType;
  status: AuditStatus;
  channel?: MessageChannel;
  recipientId?: string;
  notificationId?: string;
  messageId?: string;
  duration?: number;
  errorCode?: string;
  errorMessage?: string;
  metadata?: Record<string, any>;
  correlationId?: string;
}

/**
 * Interface for audit query filters
 */
export interface IAuditQueryFilters {
  eventTypes?: AuditEventType[];
  statuses?: AuditStatus[];
  channels?: MessageChannel[];
  recipientId?: string;
  notificationId?: string;
  messageId?: string;
  correlationId?: string;
  startDate?: Date;
  endDate?: Date;
  limit?: number;
  offset?: number;
  sortBy?: string;
  sortDirection?: 'ASC' | 'DESC';
}

/**
 * Interface for audit metrics filters
 */
export interface IAuditMetricsFilters {
  eventTypes?: AuditEventType[];
  channels?: MessageChannel[];
  startDate?: Date;
  endDate?: Date;
  groupBy?: 'hour' | 'day' | 'week' | 'month';
}

/**
 * Interface for audit metrics results
 */
export interface IAuditMetrics {
  totalCount: number;
  successCount: number;
  failureCount: number;
  warningCount: number;
  averageDuration: number;
  successRate: number;
  timePoints: Array<{
    timePoint: Date;
    count: number;
    successCount: number;
    failureCount: number;
    averageDuration: number;
  }>;
}

/**
 * Interface for the Audit Service
 */
export interface IAuditService {
  createAuditRecord(record: IAuditRecordCreate): Promise<IAuditRecord>;
  queryAuditRecords(filters: IAuditQueryFilters): Promise<IAuditRecord[]>;
  getAuditRecordById(id: string): Promise<IAuditRecord | null>;
  getAuditRecordsByNotificationId(notificationId: string): Promise<IAuditRecord[]>;
  getAuditRecordsByRecipientId(recipientId: string): Promise<IAuditRecord[]>;
  getAuditRecordsByDateRange(startDate: Date, endDate: Date): Promise<IAuditRecord[]>;
  getAuditRecordsByStatus(status: AuditStatus): Promise<IAuditRecord[]>;
  getAuditRecordsByEventType(eventType: AuditEventType): Promise<IAuditRecord[]>;
  getAuditRecordsByChannel(channel: MessageChannel): Promise<IAuditRecord[]>;
  getAuditMetrics(filters: IAuditMetricsFilters): Promise<IAuditMetrics>;
  getServiceStatus(): Promise<IServiceStatus>;
}

/**
 * Implementation of the Audit Service
 */
export class AuditService implements IAuditService {
  private logger: Logger;
  private dbPool: Pool;
  private initialized: boolean = false;
  private serviceStartTime: Date;
  private storageType: 'postgres' | 'memory' | 'file';
  private memoryStorage: IAuditRecord[] = [];
  private filePath?: string;
  
  /**
   * Constructor for the AuditService
   * @param dbPool - PostgreSQL connection pool
   * @param logger - Winston logger instance
   * @param storageType - Storage backend type (postgres, memory, or file)
   * @param filePath - Path to file storage (if using file storage)
   */
  constructor(
    dbPool?: Pool,
    logger?: Logger,
    storageType: 'postgres' | 'memory' | 'file' = 'postgres',
    filePath?: string
  ) {
    this.logger = logger || global.logger || console;
    this.dbPool = dbPool;
    this.serviceStartTime = new Date();
    this.storageType = storageType;
    this.filePath = filePath;
    
    // Log service initialization
    this.logger.info('Audit Service initialized', {
      service: 'AuditService',
      storageType: this.storageType,
      timestamp: this.serviceStartTime
    });
    
    // Create an initial audit record for service start
    this.createAuditRecord({
      eventType: AuditEventType.SERVICE_STARTED,
      status: AuditStatus.INFO,
      metadata: {
        version: appConfig.version,
        environment: appConfig.environment,
        storageType: this.storageType
      }
    }).catch(err => {
      this.logger.error('Failed to create service start audit record', {
        service: 'AuditService',
        error: err.message,
        stack: err.stack
      });
    });
  }
  
  /**
   * Initialize the audit service
   */
  public async initialize(): Promise<void> {
    if (this.initialized) {
      return;
    }
    
    try {
      if (this.storageType === 'postgres' && this.dbPool) {
        // Ensure the audit_records table exists
        await this.ensureTableExists();
      } else if (this.storageType === 'file' && this.filePath) {
        // Ensure the file storage is ready
        await this.ensureFileStorageReady();
      }
      
      this.initialized = true;
      this.logger.info('Audit Service successfully initialized', {
        service: 'AuditService',
        storageType: this.storageType
      });
    } catch (error) {
      this.logger.error('Failed to initialize Audit Service', {
        service: 'AuditService',
        error: error.message,
        stack: error.stack
      });
      throw error;
    }
  }
  
  /**
   * Create a new audit record
   * @param record - The audit record to create
   * @returns The created audit record
   */
  public async createAuditRecord(record: IAuditRecordCreate): Promise<IAuditRecord> {
    try {
      // Ensure the service is initialized
      if (!this.initialized) {
        await this.initialize();
      }
      
      const now = new Date();
      const auditRecord: IAuditRecord = {
        id: uuidv4(),
        timestamp: now,
        eventType: record.eventType,
        status: record.status,
        channel: record.channel,
        recipientId: record.recipientId,
        notificationId: record.notificationId,
        messageId: record.messageId,
        duration: record.duration,
        errorCode: record.errorCode,
        errorMessage: record.errorMessage,
        metadata: record.metadata || {},
        correlationId: record.correlationId || uuidv4(),
        createdAt: now,
        updatedAt: now
      };
      
      // Store the audit record based on the configured storage type
      if (this.storageType === 'postgres' && this.dbPool) {
        return await this.storeAuditRecordInPostgres(auditRecord);
      } else if (this.storageType === 'file' && this.filePath) {
        return await this.storeAuditRecordInFile(auditRecord);
      } else {
        // Default to memory storage
        return this.storeAuditRecordInMemory(auditRecord);
      }
    } catch (error) {
      this.logger.error('Failed to create audit record', {
        service: 'AuditService',
        eventType: record.eventType,
        error: error.message,
        stack: error.stack
      });
      
      // Even if storage fails, return a valid audit record
      // This ensures the calling code can continue without errors
      const fallbackRecord: IAuditRecord = {
        id: uuidv4(),
        timestamp: new Date(),
        eventType: record.eventType,
        status: record.status,
        channel: record.channel,
        recipientId: record.recipientId,
        notificationId: record.notificationId,
        messageId: record.messageId,
        duration: record.duration,
        errorCode: record.errorCode || 'AUDIT_STORAGE_ERROR',
        errorMessage: record.errorMessage || `Failed to store audit record: ${error.message}`,
        metadata: record.metadata || {},
        correlationId: record.correlationId || uuidv4(),
        createdAt: new Date(),
        updatedAt: new Date()
      };
      
      // Store the error in memory as a fallback
      this.memoryStorage.push(fallbackRecord);
      
      return fallbackRecord;
    }
  }
  
  /**
   * Query audit records based on filters
   * @param filters - The filters to apply to the query
   * @returns An array of matching audit records
   */
  public async queryAuditRecords(filters: IAuditQueryFilters): Promise<IAuditRecord[]> {
    try {
      // Ensure the service is initialized
      if (!this.initialized) {
        await this.initialize();
      }
      
      // Query the audit records based on the configured storage type
      if (this.storageType === 'postgres' && this.dbPool) {
        return await this.queryAuditRecordsFromPostgres(filters);
      } else if (this.storageType === 'file' && this.filePath) {
        return await this.queryAuditRecordsFromFile(filters);
      } else {
        // Default to memory storage
        return this.queryAuditRecordsFromMemory(filters);
      }
    } catch (error) {
      this.logger.error('Failed to query audit records', {
        service: 'AuditService',
        filters,
        error: error.message,
        stack: error.stack
      });
      
      // Return an empty array on error to prevent calling code from breaking
      return [];
    }
  }
  
  /**
   * Get an audit record by ID
   * @param id - The ID of the audit record to retrieve
   * @returns The audit record or null if not found
   */
  public async getAuditRecordById(id: string): Promise<IAuditRecord | null> {
    try {
      const records = await this.queryAuditRecords({ limit: 1 });
      return records.find(record => record.id === id) || null;
    } catch (error) {
      this.logger.error('Failed to get audit record by ID', {
        service: 'AuditService',
        id,
        error: error.message,
        stack: error.stack
      });
      return null;
    }
  }
  
  /**
   * Get audit records by notification ID
   * @param notificationId - The notification ID to filter by
   * @returns An array of matching audit records
   */
  public async getAuditRecordsByNotificationId(notificationId: string): Promise<IAuditRecord[]> {
    return this.queryAuditRecords({ notificationId });
  }
  
  /**
   * Get audit records by recipient ID
   * @param recipientId - The recipient ID to filter by
   * @returns An array of matching audit records
   */
  public async getAuditRecordsByRecipientId(recipientId: string): Promise<IAuditRecord[]> {
    return this.queryAuditRecords({ recipientId });
  }
  
  /**
   * Get audit records by date range
   * @param startDate - The start date of the range
   * @param endDate - The end date of the range
   * @returns An array of matching audit records
   */
  public async getAuditRecordsByDateRange(startDate: Date, endDate: Date): Promise<IAuditRecord[]> {
    return this.queryAuditRecords({ startDate, endDate });
  }
  
  /**
   * Get audit records by status
   * @param status - The status to filter by
   * @returns An array of matching audit records
   */
  public async getAuditRecordsByStatus(status: AuditStatus): Promise<IAuditRecord[]> {
    return this.queryAuditRecords({ statuses: [status] });
  }
  
  /**
   * Get audit records by event type
   * @param eventType - The event type to filter by
   * @returns An array of matching audit records
   */
  public async getAuditRecordsByEventType(eventType: AuditEventType): Promise<IAuditRecord[]> {
    return this.queryAuditRecords({ eventTypes: [eventType] });
  }
  
  /**
   * Get audit records by channel
   * @param channel - The channel to filter by
   * @returns An array of matching audit records
   */
  public async getAuditRecordsByChannel(channel: MessageChannel): Promise<IAuditRecord[]> {
    return this.queryAuditRecords({ channels: [channel] });
  }
  
  /**
   * Get audit metrics based on filters
   * @param filters - The filters to apply to the metrics calculation
   * @returns Audit metrics
   */
  public async getAuditMetrics(filters: IAuditMetricsFilters): Promise<IAuditMetrics> {
    try {
      // Ensure the service is initialized
      if (!this.initialized) {
        await this.initialize();
      }
      
      // Set default dates if not provided
      const startDate = filters.startDate || new Date(Date.now() - 24 * 60 * 60 * 1000); // Default to last 24 hours
      const endDate = filters.endDate || new Date();
      const groupBy = filters.groupBy || 'hour';
      
      // Query audit records for the specified period
      const records = await this.queryAuditRecords({
        eventTypes: filters.eventTypes,
        channels: filters.channels,
        startDate,
        endDate,
        sortBy: 'timestamp',
        sortDirection: 'ASC'
      });
      
      // Calculate basic metrics
      const totalCount = records.length;
      const successCount = records.filter(r => r.status === AuditStatus.SUCCESS).length;
      const failureCount = records.filter(r => r.status === AuditStatus.FAILURE).length;
      const warningCount = records.filter(r => r.status === AuditStatus.WARNING).length;
      
      // Calculate average duration (only for records that have duration)
      const recordsWithDuration = records.filter(r => r.duration !== undefined && r.duration !== null);
      const totalDuration = recordsWithDuration.reduce((sum, record) => sum + (record.duration || 0), 0);
      const averageDuration = recordsWithDuration.length > 0 ? totalDuration / recordsWithDuration.length : 0;
      
      // Calculate success rate
      const successRate = totalCount > 0 ? (successCount / totalCount) * 100 : 0;
      
      // Group records by time points based on the groupBy parameter
      const timePoints = this.groupRecordsByTimePoints(records, startDate, endDate, groupBy);
      
      return {
        totalCount,
        successCount,
        failureCount,
        warningCount,
        averageDuration,
        successRate,
        timePoints
      };
    } catch (error) {
      this.logger.error('Failed to get audit metrics', {
        service: 'AuditService',
        filters,
        error: error.message,
        stack: error.stack
      });
      
      // Return default metrics on error
      return {
        totalCount: 0,
        successCount: 0,
        failureCount: 0,
        warningCount: 0,
        averageDuration: 0,
        successRate: 0,
        timePoints: []
      };
    }
  }
  
  /**
   * Get the service status
   * @returns The service status
   */
  public async getServiceStatus(): Promise<IServiceStatus> {
    const uptime = Date.now() - this.serviceStartTime.getTime();
    let status: 'healthy' | 'degraded' | 'unhealthy' = 'healthy';
    let message = 'Audit service is healthy';
    
    try {
      // Check storage health
      if (this.storageType === 'postgres' && this.dbPool) {
        const client = await this.dbPool.connect();
        try {
          await client.query('SELECT 1');
        } finally {
          client.release();
        }
      }
    } catch (error) {
      status = 'degraded';
      message = `Audit service is degraded: ${error.message}`;
      
      this.logger.warn('Audit service health check failed', {
        service: 'AuditService',
        error: error.message,
        stack: error.stack
      });
    }
    
    return {
      service: 'AuditService',
      status,
      message,
      version: appConfig.version,
      uptime,
      timestamp: new Date()
    };
  }
  
  /**
   * Ensure the audit_records table exists in PostgreSQL
   * @private
   */
  private async ensureTableExists(): Promise<void> {
    if (!this.dbPool) {
      throw new Error('Database pool is not initialized');
    }
    
    const client = await this.dbPool.connect();
    try {
      // Create the audit_records table if it doesn't exist
      await client.query(`
        CREATE TABLE IF NOT EXISTS audit_records (
          id UUID PRIMARY KEY,
          timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
          event_type VARCHAR(50) NOT NULL,
          status VARCHAR(20) NOT NULL,
          channel VARCHAR(20),
          recipient_id VARCHAR(100),
          notification_id VARCHAR(100),
          message_id VARCHAR(100),
          duration INTEGER,
          error_code VARCHAR(50),
          error_message TEXT,
          metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
          correlation_id VARCHAR(100) NOT NULL,
          created_at TIMESTAMP WITH TIME ZONE NOT NULL,
          updated_at TIMESTAMP WITH TIME ZONE NOT NULL
        );
        
        -- Create indexes for common query patterns
        CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_records(timestamp);
        CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_records(event_type);
        CREATE INDEX IF NOT EXISTS idx_audit_status ON audit_records(status);
        CREATE INDEX IF NOT EXISTS idx_audit_correlation_id ON audit_records(correlation_id);
        CREATE INDEX IF NOT EXISTS idx_audit_notification_id ON audit_records(notification_id);
        CREATE INDEX IF NOT EXISTS idx_audit_recipient_id ON audit_records(recipient_id);
      `);
      
      this.logger.info('Audit records table ensured', {
        service: 'AuditService'
      });
    } catch (error) {
      this.logger.error('Failed to ensure audit_records table exists', {
        service: 'AuditService',
        error: error.message,
        stack: error.stack
      });
      throw error;
    } finally {
      client.release();
    }
  }
  
  /**
   * Ensure file storage is ready
   * @private
   */
  private async ensureFileStorageReady(): Promise<void> {
    // Implementation would depend on the file system access library
    // For simplicity, we'll just log a message
    this.logger.info('File storage ready for audit records', {
      service: 'AuditService',
      filePath: this.filePath
    });
  }
  
  /**
   * Store an audit record in PostgreSQL
   * @param record - The audit record to store
   * @returns The stored audit record
   * @private
   */
  private async storeAuditRecordInPostgres(record: IAuditRecord): Promise<IAuditRecord> {
    if (!this.dbPool) {
      throw new Error('Database pool is not initialized');
    }
    
    const client = await this.dbPool.connect();
    try {
      const result = await client.query(
        `INSERT INTO audit_records (
          id, timestamp, event_type, status, channel, recipient_id, notification_id, 
          message_id, duration, error_code, error_message, metadata, correlation_id, 
          created_at, updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15) 
        RETURNING *`,
        [
          record.id,
          record.timestamp,
          record.eventType,
          record.status,
          record.channel,
          record.recipientId,
          record.notificationId,
          record.messageId,
          record.duration,
          record.errorCode,
          record.errorMessage,
          JSON.stringify(record.metadata),
          record.correlationId,
          record.createdAt,
          record.updatedAt
        ]
      );
      
      // Map the database record back to our interface
      const dbRecord = result.rows[0];
      return {
        id: dbRecord.id,
        timestamp: dbRecord.timestamp,
        eventType: dbRecord.event_type,
        status: dbRecord.status,
        channel: dbRecord.channel,
        recipientId: dbRecord.recipient_id,
        notificationId: dbRecord.notification_id,
        messageId: dbRecord.message_id,
        duration: dbRecord.duration,
        errorCode: dbRecord.error_code,
        errorMessage: dbRecord.error_message,
        metadata: dbRecord.metadata,
        correlationId: dbRecord.correlation_id,
        createdAt: dbRecord.created_at,
        updatedAt: dbRecord.updated_at
      };
    } catch (error) {
      this.logger.error('Failed to store audit record in PostgreSQL', {
        service: 'AuditService',
        recordId: record.id,
        error: error.message,
        stack: error.stack
      });
      throw error;
    } finally {
      client.release();
    }
  }
  
  /**
   * Store an audit record in a file
   * @param record - The audit record to store
   * @returns The stored audit record
   * @private
   */
  private async storeAuditRecordInFile(record: IAuditRecord): Promise<IAuditRecord> {
    // Implementation would depend on the file system access library
    // For simplicity, we'll just log a message and store in memory
    this.logger.info('Storing audit record in file', {
      service: 'AuditService',
      recordId: record.id,
      filePath: this.filePath
    });
    
    // Store in memory as a fallback
    return this.storeAuditRecordInMemory(record);
  }
  
  /**
   * Store an audit record in memory
   * @param record - The audit record to store
   * @returns The stored audit record
   * @private
   */
  private storeAuditRecordInMemory(record: IAuditRecord): IAuditRecord {
    // Add to memory storage
    this.memoryStorage.push(record);
    
    // Limit memory storage size to prevent memory leaks
    const maxMemoryRecords = 1000;
    if (this.memoryStorage.length > maxMemoryRecords) {
      this.memoryStorage = this.memoryStorage.slice(-maxMemoryRecords);
    }
    
    return record;
  }
  
  /**
   * Query audit records from PostgreSQL
   * @param filters - The filters to apply to the query
   * @returns An array of matching audit records
   * @private
   */
  private async queryAuditRecordsFromPostgres(filters: IAuditQueryFilters): Promise<IAuditRecord[]> {
    if (!this.dbPool) {
      throw new Error('Database pool is not initialized');
    }
    
    const client = await this.dbPool.connect();
    try {
      // Build the query
      let query = 'SELECT * FROM audit_records WHERE 1=1';
      const params: any[] = [];
      let paramIndex = 1;
      
      // Add filters
      if (filters.eventTypes && filters.eventTypes.length > 0) {
        query += ` AND event_type IN (${filters.eventTypes.map(() => `$${paramIndex++}`).join(', ')})`;
        params.push(...filters.eventTypes);
      }
      
      if (filters.statuses && filters.statuses.length > 0) {
        query += ` AND status IN (${filters.statuses.map(() => `$${paramIndex++}`).join(', ')})`;
        params.push(...filters.statuses);
      }
      
      if (filters.channels && filters.channels.length > 0) {
        query += ` AND channel IN (${filters.channels.map(() => `$${paramIndex++}`).join(', ')})`;
        params.push(...filters.channels);
      }
      
      if (filters.recipientId) {
        query += ` AND recipient_id = $${paramIndex++}`;
        params.push(filters.recipientId);
      }
      
      if (filters.notificationId) {
        query += ` AND notification_id = $${paramIndex++}`;
        params.push(filters.notificationId);
      }
      
      if (filters.messageId) {
        query += ` AND message_id = $${paramIndex++}`;
        params.push(filters.messageId);
      }
      
      if (filters.correlationId) {
        query += ` AND correlation_id = $${paramIndex++}`;
        params.push(filters.correlationId);
      }
      
      if (filters.startDate) {
        query += ` AND timestamp >= $${paramIndex++}`;
        params.push(filters.startDate);
      }
      
      if (filters.endDate) {
        query += ` AND timestamp <= $${paramIndex++}`;
        params.push(filters.endDate);
      }
      
      // Add sorting
      const sortBy = filters.sortBy || 'timestamp';
      const sortDirection = filters.sortDirection || 'DESC';
      query += ` ORDER BY ${this.mapSortFieldToColumn(sortBy)} ${sortDirection}`;
      
      // Add pagination
      if (filters.limit) {
        query += ` LIMIT $${paramIndex++}`;
        params.push(filters.limit);
      }
      
      if (filters.offset) {
        query += ` OFFSET $${paramIndex++}`;
        params.push(filters.offset);
      }
      
      // Execute the query
      const result = await client.query(query, params);
      
      // Map the database records to our interface
      return result.rows.map(row => ({
        id: row.id,
        timestamp: row.timestamp,
        eventType: row.event_type,
        status: row.status,
        channel: row.channel,
        recipientId: row.recipient_id,
        notificationId: row.notification_id,
        messageId: row.message_id,
        duration: row.duration,
        errorCode: row.error_code,
        errorMessage: row.error_message,
        metadata: row.metadata,
        correlationId: row.correlation_id,
        createdAt: row.created_at,
        updatedAt: row.updated_at
      }));
    } catch (error) {
      this.logger.error('Failed to query audit records from PostgreSQL', {
        service: 'AuditService',
        filters,
        error: error.message,
        stack: error.stack
      });
      throw error;
    } finally {
      client.release();
    }
  }
  
  /**
   * Query audit records from a file
   * @param filters - The filters to apply to the query
   * @returns An array of matching audit records
   * @private
   */
  private async queryAuditRecordsFromFile(filters: IAuditQueryFilters): Promise<IAuditRecord[]> {
    // Implementation would depend on the file system access library
    // For simplicity, we'll just log a message and query from memory
    this.logger.info('Querying audit records from file', {
      service: 'AuditService',
      filters,
      filePath: this.filePath
    });
    
    // Query from memory as a fallback
    return this.queryAuditRecordsFromMemory(filters);
  }
  
  /**
   * Query audit records from memory
   * @param filters - The filters to apply to the query
   * @returns An array of matching audit records
   * @private
   */
  private queryAuditRecordsFromMemory(filters: IAuditQueryFilters): IAuditRecord[] {
    let records = [...this.memoryStorage];
    
    // Apply filters
    if (filters.eventTypes && filters.eventTypes.length > 0) {
      records = records.filter(record => filters.eventTypes.includes(record.eventType));
    }
    
    if (filters.statuses && filters.statuses.length > 0) {
      records = records.filter(record => filters.statuses.includes(record.status));
    }
    
    if (filters.channels && filters.channels.length > 0) {
      records = records.filter(record => record.channel && filters.channels.includes(record.channel));
    }
    
    if (filters.recipientId) {
      records = records.filter(record => record.recipientId === filters.recipientId);
    }
    
    if (filters.notificationId) {
      records = records.filter(record => record.notificationId === filters.notificationId);
    }
    
    if (filters.messageId) {
      records = records.filter(record => record.messageId === filters.messageId);
    }
    
    if (filters.correlationId) {
      records = records.filter(record => record.correlationId === filters.correlationId);
    }
    
    if (filters.startDate) {
      records = records.filter(record => record.timestamp >= filters.startDate);
    }
    
    if (filters.endDate) {
      records = records.filter(record => record.timestamp <= filters.endDate);
    }
    
    // Apply sorting
    const sortBy = filters.sortBy || 'timestamp';
    const sortDirection = filters.sortDirection || 'DESC';
    records.sort((a, b) => {
      const aValue = a[sortBy];
      const bValue = b[sortBy];
      
      if (aValue < bValue) {
        return sortDirection === 'ASC' ? -1 : 1;
      }
      if (aValue > bValue) {
        return sortDirection === 'ASC' ? 1 : -1;
      }
      return 0;
    });
    
    // Apply pagination
    if (filters.offset) {
      records = records.slice(filters.offset);
    }
    
    if (filters.limit) {
      records = records.slice(0, filters.limit);
    }
    
    return records;
  }
  
  /**
   * Group records by time points for metrics calculation
   * @param records - The records to group
   * @param startDate - The start date of the range
   * @param endDate - The end date of the range
   * @param groupBy - The time unit to group by
   * @returns An array of time points with metrics
   * @private
   */
  private groupRecordsByTimePoints(
    records: IAuditRecord[],
    startDate: Date,
    endDate: Date,
    groupBy: 'hour' | 'day' | 'week' | 'month'
  ): Array<{
    timePoint: Date;
    count: number;
    successCount: number;
    failureCount: number;
    averageDuration: number;
  }> {
    // Generate time points based on the groupBy parameter
    const timePoints: Date[] = [];
    let currentDate = new Date(startDate);
    
    while (currentDate <= endDate) {
      timePoints.push(new Date(currentDate));
      
      // Increment the date based on the groupBy parameter
      switch (groupBy) {
        case 'hour':
          currentDate = new Date(currentDate.getTime() + 60 * 60 * 1000);
          break;
        case 'day':
          currentDate = new Date(currentDate.getTime() + 24 * 60 * 60 * 1000);
          break;
        case 'week':
          currentDate = new Date(currentDate.getTime() + 7 * 24 * 60 * 60 * 1000);
          break;
        case 'month':
          currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, currentDate.getDate());
          break;
      }
    }
    
    // Group records by time points
    return timePoints.map((timePoint, index) => {
      const nextTimePoint = index < timePoints.length - 1 ? timePoints[index + 1] : new Date(endDate.getTime() + 1);
      
      // Get records for this time point
      const pointRecords = records.filter(record => {
        return record.timestamp >= timePoint && record.timestamp < nextTimePoint;
      });
      
      // Calculate metrics for this time point
      const count = pointRecords.length;
      const successCount = pointRecords.filter(r => r.status === AuditStatus.SUCCESS).length;
      const failureCount = pointRecords.filter(r => r.status === AuditStatus.FAILURE).length;
      
      // Calculate average duration
      const recordsWithDuration = pointRecords.filter(r => r.duration !== undefined && r.duration !== null);
      const totalDuration = recordsWithDuration.reduce((sum, record) => sum + (record.duration || 0), 0);
      const averageDuration = recordsWithDuration.length > 0 ? totalDuration / recordsWithDuration.length : 0;
      
      return {
        timePoint,
        count,
        successCount,
        failureCount,
        averageDuration
      };
    });
  }
  
  /**
   * Map a sort field to a database column name
   * @param field - The field to map
   * @returns The corresponding database column name
   * @private
   */
  private mapSortFieldToColumn(field: string): string {
    const columnMap: Record<string, string> = {
      id: 'id',
      timestamp: 'timestamp',
      eventType: 'event_type',
      status: 'status',
      channel: 'channel',
      recipientId: 'recipient_id',
      notificationId: 'notification_id',
      messageId: 'message_id',
      duration: 'duration',
      errorCode: 'error_code',
      correlationId: 'correlation_id',
      createdAt: 'created_at',
      updatedAt: 'updated_at'
    };
    
    return columnMap[field] || 'timestamp';
  }
}

// Export a default instance for use throughout the application
export const auditService = new AuditService();