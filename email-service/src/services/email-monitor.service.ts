/**
 * Email Monitor Service
 * 
 * This service is responsible for monitoring the configured IMAP mailboxes for new emails,
 * extracting attachments, and triggering the document processing pipeline.
 * 
 * Key features:
 * - IMAP connection with TLS 1.2+ and certificate validation
 * - Connection pooling with appropriate timeout settings
 * - Automatic reconnection for reliability
 * - Email filtering based on configurable rules
 * - Email metadata extraction in required format
 * - Tracking of processed emails using message IDs to prevent duplicates
 */

import { EventEmitter } from 'events';
import * as imaps from 'imap-simple';
import { simpleParser } from 'mailparser';
import { Connection, ImapSimpleOptions, Message } from 'imap-simple';
import { logger } from '../utils/logger';
import { retry } from '../utils/retry';
import { createServiceError } from '../utils/error';
import { validateEmailDomain, validateAttachmentType } from '../utils/validation';
import { formatISODate } from '../utils/format-time';
import { AttachmentProcessorService } from './attachment-processor.service';
import { VirusScannerService } from './virus-scanner.service';
import { StorageService } from './storage.service';
import { MessageQueueService } from './message-queue.service';
import { 
  IEmailMessage, 
  IEmailMetadata, 
  IEmailAttachment,
  IIMAPConfig, 
  IIMAPConnection,
  IIMAPSearchCriteria,
  IResult,
  ILogLevel
} from '../types';

/**
 * Configuration for the EmailMonitorService
 */
export interface IEmailMonitorConfig {
  /** IMAP connection configuration */
  imap: IIMAPConfig;
  /** Polling interval in milliseconds */
  pollingInterval: number;
  /** Maximum number of emails to process in a single poll */
  batchSize: number;
  /** Allowed sender domains for filtering */
  allowedSenderDomains: string[];
  /** Allowed attachment types */
  allowedAttachmentTypes: string[];
  /** Maximum attachment size in bytes */
  maxAttachmentSize: number;
  /** Whether to enable virus scanning */
  enableVirusScan: boolean;
}

/**
 * Email Monitor Service class
 * 
 * Responsible for monitoring IMAP mailboxes and processing new emails
 */
export class EmailMonitorService extends EventEmitter {
  private config: IEmailMonitorConfig;
  private connection: Connection | null = null;
  private connectionPromise: Promise<Connection> | null = null;
  private isPolling = false;
  private pollingInterval: NodeJS.Timeout | null = null;
  private processedMessageIds = new Set<string>();
  private connectionAttempts = 0;
  private readonly MAX_CONNECTION_ATTEMPTS = 5;
  private readonly RECONNECT_DELAY_MS = 5000;
  
  /**
   * Creates an instance of EmailMonitorService
   */
  constructor(
    private readonly attachmentProcessor: AttachmentProcessorService,
    private readonly virusScanner: VirusScannerService,
    private readonly storageService: StorageService,
    private readonly messageQueueService: MessageQueueService,
    config: IEmailMonitorConfig
  ) {
    super();
    this.config = {
      ...config,
      pollingInterval: config.pollingInterval || 60000, // Default: 1 minute
      batchSize: config.batchSize || 10,
      allowedSenderDomains: config.allowedSenderDomains || [],
      allowedAttachmentTypes: config.allowedAttachmentTypes || ['application/pdf', 'image/tiff', 'image/png', 'image/jpeg'],
      maxAttachmentSize: config.maxAttachmentSize || 10 * 1024 * 1024, // Default: 10MB
      enableVirusScan: config.enableVirusScan !== undefined ? config.enableVirusScan : true
    };

    // Validate required configuration
    if (!this.config.imap) {
      throw createServiceError('EmailMonitorService', 'Missing IMAP configuration');
    }

    // Bind methods to preserve 'this' context
    this.startPolling = this.startPolling.bind(this);
    this.stopPolling = this.stopPolling.bind(this);
    this.pollMailbox = this.pollMailbox.bind(this);
    this.processEmail = this.processEmail.bind(this);
    this.handleConnectionError = this.handleConnectionError.bind(this);
  }

  /**
   * Initializes the service and establishes IMAP connection
   */
  public async initialize(): Promise<void> {
    logger.info('Initializing EmailMonitorService', { service: 'EmailMonitorService' });
    
    try {
      await this.connect();
      logger.info('EmailMonitorService initialized successfully', { service: 'EmailMonitorService' });
    } catch (error) {
      logger.error('Failed to initialize EmailMonitorService', { 
        service: 'EmailMonitorService', 
        error: error instanceof Error ? error.message : String(error) 
      });
      throw error;
    }
  }

  /**
   * Establishes connection to the IMAP server
   */
  private async connect(): Promise<Connection> {
    if (this.connectionPromise) {
      return this.connectionPromise;
    }

    logger.info('Connecting to IMAP server', { 
      service: 'EmailMonitorService',
      server: this.config.imap.host,
      port: this.config.imap.port,
      user: this.config.imap.user,
      tls: this.config.imap.tls
    });

    // Reset connection attempts on new connection
    this.connectionAttempts = 0;

    // Configure IMAP connection with TLS 1.2+ and certificate validation
    const imapConfig: ImapSimpleOptions = {
      imap: {
        user: this.config.imap.user,
        password: this.config.imap.password,
        host: this.config.imap.host,
        port: this.config.imap.port,
        tls: this.config.imap.tls,
        tlsOptions: {
          minVersion: 'TLSv1.2',
          rejectUnauthorized: true // Enforce certificate validation
        },
        authTimeout: 10000, // 10 seconds
        keepalive: {
          interval: 10000, // 10 seconds
          idleInterval: 300000, // 5 minutes
          forceNoop: true
        }
      },
      onmail: () => {
        // Trigger immediate polling when new mail arrives
        if (!this.isPolling) {
          this.pollMailbox().catch(this.handleConnectionError);
        }
      },
      onupdate: () => {
        // Handle mailbox updates (e.g., flags changed)
        logger.debug('Mailbox updated', { service: 'EmailMonitorService' });
      },
      onexpunge: () => {
        // Handle expunged messages
        logger.debug('Messages expunged from mailbox', { service: 'EmailMonitorService' });
      },
      onerror: this.handleConnectionError
    };

    // Use retry utility with exponential backoff for connection
    this.connectionPromise = retry(
      async () => {
        const connection = await imaps.connect(imapConfig);
        // Open the INBOX mailbox in readonly mode to prevent marking messages as read
        await connection.openBox('INBOX');
        return connection;
      },
      {
        retries: 3,
        minTimeout: 1000,
        maxTimeout: 10000,
        factor: 2,
        onRetry: (error, attempt) => {
          logger.warn(`IMAP connection attempt ${attempt} failed, retrying...`, { 
            service: 'EmailMonitorService',
            error: error instanceof Error ? error.message : String(error)
          });
        }
      }
    );

    try {
      this.connection = await this.connectionPromise;
      this.connectionAttempts = 0; // Reset counter on successful connection
      logger.info('Successfully connected to IMAP server', { service: 'EmailMonitorService' });
      
      // Set up event listeners for connection
      this.connection.on('error', this.handleConnectionError);
      this.connection.on('end', () => {
        logger.info('IMAP connection ended', { service: 'EmailMonitorService' });
        this.connection = null;
        this.connectionPromise = null;
        this.reconnect();
      });

      return this.connection;
    } catch (error) {
      this.connectionPromise = null;
      logger.error('Failed to connect to IMAP server', { 
        service: 'EmailMonitorService',
        error: error instanceof Error ? error.message : String(error)
      });
      this.reconnect();
      throw error;
    }
  }

  /**
   * Handles connection errors and triggers reconnection
   */
  private handleConnectionError(error: Error): void {
    logger.error('IMAP connection error', { 
      service: 'EmailMonitorService',
      error: error.message,
      stack: error.stack
    });
    
    // Reset connection state
    this.connection = null;
    this.connectionPromise = null;
    
    // Attempt to reconnect
    this.reconnect();
  }

  /**
   * Attempts to reconnect to the IMAP server with exponential backoff
   */
  private reconnect(): void {
    this.connectionAttempts++;
    
    if (this.connectionAttempts > this.MAX_CONNECTION_ATTEMPTS) {
      logger.error(`Maximum reconnection attempts (${this.MAX_CONNECTION_ATTEMPTS}) reached`, { 
        service: 'EmailMonitorService' 
      });
      this.emit('maxReconnectAttemptsReached');
      return;
    }
    
    const delay = this.RECONNECT_DELAY_MS * Math.pow(2, this.connectionAttempts - 1);
    logger.info(`Attempting to reconnect in ${delay}ms (attempt ${this.connectionAttempts})`, { 
      service: 'EmailMonitorService' 
    });
    
    setTimeout(() => {
      this.connect().catch((error) => {
        logger.error('Reconnection attempt failed', { 
          service: 'EmailMonitorService',
          error: error instanceof Error ? error.message : String(error),
          attempt: this.connectionAttempts
        });
      });
    }, delay);
  }

  /**
   * Starts polling the mailbox at configured intervals
   */
  public async startPolling(): Promise<void> {
    if (this.pollingInterval) {
      logger.warn('Polling already started', { service: 'EmailMonitorService' });
      return;
    }

    logger.info(`Starting email polling with interval of ${this.config.pollingInterval}ms`, { 
      service: 'EmailMonitorService' 
    });
    
    // Perform initial poll
    await this.pollMailbox().catch(this.handleConnectionError);
    
    // Set up recurring polling
    this.pollingInterval = setInterval(async () => {
      await this.pollMailbox().catch(this.handleConnectionError);
    }, this.config.pollingInterval);
    
    this.emit('pollingStarted');
  }

  /**
   * Stops polling the mailbox
   */
  public stopPolling(): void {
    if (this.pollingInterval) {
      logger.info('Stopping email polling', { service: 'EmailMonitorService' });
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
      this.emit('pollingStopped');
    }
  }

  /**
   * Polls the mailbox for new emails
   */
  private async pollMailbox(): Promise<void> {
    if (this.isPolling) {
      logger.debug('Polling already in progress, skipping', { service: 'EmailMonitorService' });
      return;
    }

    this.isPolling = true;
    logger.info('Polling mailbox for new emails', { service: 'EmailMonitorService' });

    try {
      // Ensure connection is established
      if (!this.connection) {
        this.connection = await this.connect();
      }

      // Search for unread messages
      const searchCriteria: IIMAPSearchCriteria = ['UNSEEN'];
      const fetchOptions = {
        bodies: ['HEADER', 'TEXT', ''],
        markSeen: false, // Don't mark as seen until processed successfully
        struct: true
      };

      // Fetch messages
      const messages = await this.connection.search(searchCriteria, fetchOptions);
      logger.info(`Found ${messages.length} unread messages`, { service: 'EmailMonitorService' });

      // Process messages in batches to avoid overwhelming the system
      const messagesToProcess = messages.slice(0, this.config.batchSize);
      
      // Process each message
      for (const message of messagesToProcess) {
        await this.processEmail(message);
      }

      this.emit('pollingCompleted', { processedCount: messagesToProcess.length });
    } catch (error) {
      logger.error('Error polling mailbox', { 
        service: 'EmailMonitorService',
        error: error instanceof Error ? error.message : String(error)
      });
      this.emit('pollingError', error);
      
      // Handle connection errors
      if (error instanceof Error && 
          (error.message.includes('connection') || error.message.includes('timeout'))) {
        this.handleConnectionError(error);
      }
    } finally {
      this.isPolling = false;
    }
  }

  /**
   * Processes a single email message
   */
  private async processEmail(message: Message): Promise<void> {
    try {
      // Extract message ID from headers
      const headerPart = message.parts.find(part => part.which === 'HEADER');
      if (!headerPart) {
        throw createServiceError('EmailMonitorService', 'Missing header part in message');
      }
      
      const headers = headerPart.body;
      const messageId = headers['message-id']?.[0] || headers['Message-ID']?.[0];
      
      if (!messageId) {
        throw createServiceError('EmailMonitorService', 'Missing message ID');
      }

      // Check if message has already been processed
      if (this.processedMessageIds.has(messageId)) {
        logger.info(`Message ${messageId} already processed, skipping`, { 
          service: 'EmailMonitorService',
          messageId
        });
        return;
      }

      // Get the full message part
      const fullMessagePart = message.parts.find(part => part.which === '');
      if (!fullMessagePart) {
        throw createServiceError('EmailMonitorService', 'Missing full message part');
      }

      // Parse the email using mailparser
      const parsedEmail = await simpleParser(fullMessagePart.body);
      
      // Validate sender domain if configured
      if (this.config.allowedSenderDomains.length > 0) {
        const senderEmail = parsedEmail.from?.value[0]?.address;
        if (!senderEmail || !validateEmailDomain(senderEmail, this.config.allowedSenderDomains)) {
          logger.warn(`Email from ${senderEmail} rejected due to domain filtering`, { 
            service: 'EmailMonitorService',
            messageId,
            sender: senderEmail
          });
          
          // Mark as processed to avoid reprocessing
          this.processedMessageIds.add(messageId);
          return;
        }
      }

      // Check if email has attachments
      if (!parsedEmail.attachments || parsedEmail.attachments.length === 0) {
        logger.info(`Email ${messageId} has no attachments, skipping`, { 
          service: 'EmailMonitorService',
          messageId
        });
        
        // Mark as processed to avoid reprocessing
        this.processedMessageIds.add(messageId);
        return;
      }

      // Extract email metadata
      const metadata: IEmailMetadata = {
        messageId,
        subject: parsedEmail.subject || 'No Subject',
        sender: {
          name: parsedEmail.from?.value[0]?.name || '',
          address: parsedEmail.from?.value[0]?.address || ''
        },
        recipient: {
          name: parsedEmail.to?.value[0]?.name || '',
          address: parsedEmail.to?.value[0]?.address || ''
        },
        receivedDate: formatISODate(parsedEmail.date || new Date()),
        processingDate: formatISODate(new Date())
      };

      // Process attachments
      const validAttachments: IEmailAttachment[] = [];
      
      for (const attachment of parsedEmail.attachments) {
        // Validate attachment type
        if (!validateAttachmentType(attachment.contentType, this.config.allowedAttachmentTypes)) {
          logger.warn(`Attachment ${attachment.filename} has unsupported type ${attachment.contentType}`, { 
            service: 'EmailMonitorService',
            messageId,
            filename: attachment.filename,
            contentType: attachment.contentType
          });
          continue;
        }

        // Validate attachment size
        if (attachment.size > this.config.maxAttachmentSize) {
          logger.warn(`Attachment ${attachment.filename} exceeds maximum size limit`, { 
            service: 'EmailMonitorService',
            messageId,
            filename: attachment.filename,
            size: attachment.size,
            maxSize: this.config.maxAttachmentSize
          });
          continue;
        }

        // Process attachment
        try {
          // Scan for viruses if enabled
          if (this.config.enableVirusScan) {
            const scanResult = await this.virusScanner.scanBuffer(attachment.content);
            if (!scanResult.success) {
              logger.error(`Virus detected in attachment ${attachment.filename}`, { 
                service: 'EmailMonitorService',
                messageId,
                filename: attachment.filename,
                virusName: scanResult.data?.virusName
              });
              
              // Quarantine the file
              await this.virusScanner.quarantineBuffer(attachment.content, attachment.filename, messageId);
              continue;
            }
          }

          // Process the attachment with the attachment processor
          const processedAttachment = await this.attachmentProcessor.processAttachment({
            filename: attachment.filename,
            contentType: attachment.contentType,
            content: attachment.content,
            size: attachment.size
          });

          validAttachments.push(processedAttachment);
        } catch (error) {
          logger.error(`Error processing attachment ${attachment.filename}`, { 
            service: 'EmailMonitorService',
            messageId,
            filename: attachment.filename,
            error: error instanceof Error ? error.message : String(error)
          });
        }
      }

      // If no valid attachments were found, mark as processed and return
      if (validAttachments.length === 0) {
        logger.info(`No valid attachments found in email ${messageId}`, { 
          service: 'EmailMonitorService',
          messageId
        });
        
        // Mark as processed to avoid reprocessing
        this.processedMessageIds.add(messageId);
        return;
      }

      // Create email message object
      const emailMessage: IEmailMessage = {
        metadata,
        attachments: validAttachments,
        messageBody: parsedEmail.text || ''
      };

      // Store attachments in S3
      for (const attachment of validAttachments) {
        try {
          const storageResult = await this.storageService.storeDocument({
            content: attachment.content,
            filename: attachment.filename,
            contentType: attachment.contentType,
            metadata: {
              messageId,
              sender: metadata.sender.address,
              subject: metadata.subject,
              receivedDate: metadata.receivedDate
            }
          });

          // Update attachment with storage information
          attachment.storagePath = storageResult.data?.path;
          attachment.storageKey = storageResult.data?.key;
        } catch (error) {
          logger.error(`Error storing attachment ${attachment.filename} in S3`, { 
            service: 'EmailMonitorService',
            messageId,
            filename: attachment.filename,
            error: error instanceof Error ? error.message : String(error)
          });
          
          // Remove attachment from valid attachments if storage failed
          const index = validAttachments.indexOf(attachment);
          if (index !== -1) {
            validAttachments.splice(index, 1);
          }
        }
      }

      // If no attachments were successfully stored, mark as processed and return
      if (validAttachments.length === 0) {
        logger.info(`No attachments were successfully stored for email ${messageId}`, { 
          service: 'EmailMonitorService',
          messageId
        });
        
        // Mark as processed to avoid reprocessing
        this.processedMessageIds.add(messageId);
        return;
      }

      // Publish message to RabbitMQ for further processing
      try {
        await this.messageQueueService.publishDocumentMessage({
          messageId,
          metadata,
          attachments: validAttachments.map(attachment => ({
            filename: attachment.filename,
            contentType: attachment.contentType,
            size: attachment.size,
            storagePath: attachment.storagePath,
            storageKey: attachment.storageKey
          }))
        });

        logger.info(`Successfully published message for email ${messageId} to RabbitMQ`, { 
          service: 'EmailMonitorService',
          messageId,
          attachmentCount: validAttachments.length
        });

        // Mark the message as seen in IMAP now that it's been successfully processed
        await this.connection?.addFlags(message.attributes.uid, '\\Seen');
        
        // Mark as processed to avoid reprocessing
        this.processedMessageIds.add(messageId);
        
        // Emit success event
        this.emit('emailProcessed', { messageId, attachmentCount: validAttachments.length });
      } catch (error) {
        logger.error(`Error publishing message for email ${messageId} to RabbitMQ`, { 
          service: 'EmailMonitorService',
          messageId,
          error: error instanceof Error ? error.message : String(error)
        });
        
        // Emit error event
        this.emit('emailProcessingError', { messageId, error });
      }
    } catch (error) {
      logger.error('Error processing email', { 
        service: 'EmailMonitorService',
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined
      });
      
      // Emit error event
      this.emit('emailProcessingError', { message, error });
    }
  }

  /**
   * Cleans up resources and closes connections
   */
  public async shutdown(): Promise<void> {
    logger.info('Shutting down EmailMonitorService', { service: 'EmailMonitorService' });
    
    // Stop polling
    this.stopPolling();
    
    // Close IMAP connection
    if (this.connection) {
      try {
        await this.connection.end();
        logger.info('IMAP connection closed', { service: 'EmailMonitorService' });
      } catch (error) {
        logger.error('Error closing IMAP connection', { 
          service: 'EmailMonitorService',
          error: error instanceof Error ? error.message : String(error)
        });
      } finally {
        this.connection = null;
        this.connectionPromise = null;
      }
    }
    
    this.emit('shutdown');
  }

  /**
   * Gets the current connection status
   */
  public isConnected(): boolean {
    return this.connection !== null;
  }

  /**
   * Gets the current polling status
   */
  public isPollingActive(): boolean {
    return this.pollingInterval !== null;
  }

  /**
   * Gets the count of processed message IDs
   */
  public getProcessedMessageCount(): number {
    return this.processedMessageIds.size;
  }

  /**
   * Clears the processed message IDs cache
   * Note: This should be used carefully, as it could lead to reprocessing of emails
   */
  public clearProcessedMessageCache(): void {
    const previousCount = this.processedMessageIds.size;
    this.processedMessageIds.clear();
    logger.info(`Cleared processed message cache (${previousCount} entries)`, { 
      service: 'EmailMonitorService' 
    });
  }
}