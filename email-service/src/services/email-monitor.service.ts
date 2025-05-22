/**
 * Email Monitor Service
 * 
 * This service is responsible for monitoring email inboxes for new applications,
 * extracting metadata, and triggering the document processing pipeline.
 * 
 * It connects to IMAP servers, polls for new emails, extracts attachments,
 * and publishes them to RabbitMQ for further processing.
 */

import { connect, ImapSimple, ImapSimpleOptions, Message } from 'imap-simple';
import { simpleParser } from 'mailparser';
import { promisify } from 'util';
import { logger } from '../utils/logger';
import { retry } from '../utils/retry';
import { validateAttachment } from '../utils/validation';
import { createError } from '../utils/error';
import { IEmailMessage, IEmailMetadata, IEmailAttachment } from '../types/email';
import { MessageQueueService } from './message-queue.service';
import { StorageService } from './storage.service';
import { VirusScannerService } from './virus-scanner.service';
import { AttachmentProcessorService } from './attachment-processor.service';
import config from '../config/app';

/**
 * Interface for the Email Monitor Service configuration
 */
interface IEmailMonitorConfig {
  host: string;
  port: number;
  user: string;
  password: string;
  tls: boolean;
  tlsOptions: {
    rejectUnauthorized: boolean;
    minVersion: string;
  };
  authTimeout: number;
  connTimeout: number;
  keepalive: boolean;
  keepaliveInterval: number;
  maxRetries: number;
  retryDelay: number;
  pollingInterval: number;
}

/**
 * Interface for processed email tracking
 */
interface IProcessedEmail {
  messageId: string;
  processedAt: Date;
}

/**
 * Email Monitor Service class
 * 
 * Responsible for monitoring email inboxes, extracting attachments,
 * and publishing them to the message queue for processing.
 */
export class EmailMonitorService {
  private connection: ImapSimple | null = null;
  private isConnected: boolean = false;
  private isPolling: boolean = false;
  private pollingInterval: NodeJS.Timeout | null = null;
  private processedEmails: Map<string, IProcessedEmail> = new Map();
  private config: IEmailMonitorConfig;

  /**
   * Constructor for the Email Monitor Service
   * 
   * @param messageQueueService - Service for publishing messages to RabbitMQ
   * @param storageService - Service for storing attachments in S3
   * @param virusScannerService - Service for scanning attachments for viruses
   * @param attachmentProcessorService - Service for processing attachments
   */
  constructor(
    private readonly messageQueueService: MessageQueueService,
    private readonly storageService: StorageService,
    private readonly virusScannerService: VirusScannerService,
    private readonly attachmentProcessorService: AttachmentProcessorService
  ) {
    // Initialize configuration from app config
    this.config = {
      host: config.email.host,
      port: config.email.port,
      user: config.email.user,
      password: config.email.password,
      tls: true,
      tlsOptions: {
        rejectUnauthorized: true,
        minVersion: 'TLSv1.2'
      },
      authTimeout: 30000, // 30 seconds
      connTimeout: 60000, // 60 seconds
      keepalive: true,
      keepaliveInterval: 300000, // 5 minutes
      maxRetries: 5,
      retryDelay: 5000, // 5 seconds
      pollingInterval: config.email.pollingInterval || 60000 // Default to 1 minute
    };

    logger.info('Email Monitor Service initialized');
  }

  /**
   * Start the email monitoring service
   * 
   * Connects to the IMAP server and starts polling for new emails
   */
  public async start(): Promise<void> {
    try {
      logger.info('Starting Email Monitor Service');
      
      await this.connect();
      this.startPolling();
      
      logger.info('Email Monitor Service started successfully');
    } catch (error) {
      logger.error('Failed to start Email Monitor Service', { error });
      throw error;
    }
  }

  /**
   * Stop the email monitoring service
   * 
   * Stops polling and disconnects from the IMAP server
   */
  public async stop(): Promise<void> {
    try {
      logger.info('Stopping Email Monitor Service');
      
      this.stopPolling();
      await this.disconnect();
      
      logger.info('Email Monitor Service stopped successfully');
    } catch (error) {
      logger.error('Failed to stop Email Monitor Service', { error });
      throw error;
    }
  }

  /**
   * Connect to the IMAP server
   * 
   * Establishes a connection to the IMAP server with TLS 1.2+ and certificate validation
   */
  private async connect(): Promise<void> {
    if (this.isConnected) {
      logger.debug('Already connected to IMAP server');
      return;
    }

    try {
      logger.info('Connecting to IMAP server', { host: this.config.host, port: this.config.port });

      // Configure IMAP connection options
      const imapOptions: ImapSimpleOptions = {
        imap: {
          user: this.config.user,
          password: this.config.password,
          host: this.config.host,
          port: this.config.port,
          tls: this.config.tls,
          tlsOptions: this.config.tlsOptions,
          authTimeout: this.config.authTimeout,
          connTimeout: this.config.connTimeout,
          keepalive: this.config.keepalive,
          keepaliveInterval: this.config.keepaliveInterval
        },
        onmail: (numNewMail) => {
          logger.info(`${numNewMail} new email(s) received`);
          // Trigger immediate polling when new mail arrives
          if (numNewMail > 0 && !this.isPolling) {
            this.pollForEmails();
          }
        },
        onexpunge: (seqno) => {
          logger.debug(`Email with sequence number ${seqno} was expunged`);
        },
        onupdate: (seqno, info) => {
          logger.debug(`Email with sequence number ${seqno} was updated`, { info });
        }
      };

      // Connect to IMAP server with retry logic
      this.connection = await retry(
        async () => await connect(imapOptions),
        {
          maxRetries: this.config.maxRetries,
          retryDelay: this.config.retryDelay,
          onRetry: (attempt) => {
            logger.warn(`Retrying IMAP connection (attempt ${attempt}/${this.config.maxRetries})`);
          }
        }
      );

      this.isConnected = true;
      logger.info('Successfully connected to IMAP server');
    } catch (error) {
      this.isConnected = false;
      logger.error('Failed to connect to IMAP server', { error });
      throw createError('ConnectionError', 'Failed to connect to IMAP server', error);
    }
  }

  /**
   * Disconnect from the IMAP server
   */
  private async disconnect(): Promise<void> {
    if (!this.isConnected || !this.connection) {
      logger.debug('Not connected to IMAP server');
      return;
    }

    try {
      logger.info('Disconnecting from IMAP server');
      
      await this.connection.end();
      
      this.connection = null;
      this.isConnected = false;
      logger.info('Successfully disconnected from IMAP server');
    } catch (error) {
      logger.error('Failed to disconnect from IMAP server', { error });
      // Reset connection state even if disconnect fails
      this.connection = null;
      this.isConnected = false;
    }
  }

  /**
   * Start polling for new emails
   * 
   * Sets up a polling interval to check for new emails periodically
   */
  private startPolling(): void {
    if (this.pollingInterval) {
      logger.debug('Polling already started');
      return;
    }

    logger.info('Starting email polling', { interval: this.config.pollingInterval });
    
    // Perform initial poll immediately
    this.pollForEmails();
    
    // Set up polling interval
    this.pollingInterval = setInterval(() => {
      this.pollForEmails();
    }, this.config.pollingInterval);
  }

  /**
   * Stop polling for new emails
   */
  private stopPolling(): void {
    if (!this.pollingInterval) {
      logger.debug('Polling not started');
      return;
    }

    logger.info('Stopping email polling');
    
    clearInterval(this.pollingInterval);
    this.pollingInterval = null;
  }

  /**
   * Poll for new emails
   * 
   * Checks the IMAP server for new emails and processes them
   */
  private async pollForEmails(): Promise<void> {
    if (this.isPolling) {
      logger.debug('Already polling for emails');
      return;
    }

    this.isPolling = true;

    try {
      // Ensure we're connected
      if (!this.isConnected) {
        await this.connect();
      }

      if (!this.connection) {
        throw createError('ConnectionError', 'IMAP connection not established');
      }

      logger.info('Polling for new emails');

      // Open the inbox
      await this.connection.openBox('INBOX');

      // Search for unread emails
      const searchCriteria = ['UNSEEN'];
      const fetchOptions = {
        bodies: ['HEADER', 'TEXT', ''],
        markSeen: false, // Don't mark as seen until processed successfully
        struct: true
      };

      // Fetch unread messages
      const messages = await this.connection.search(searchCriteria, fetchOptions);
      logger.info(`Found ${messages.length} unread email(s)`);

      // Process each message
      for (const message of messages) {
        await this.processEmail(message);
      }

      logger.info('Email polling completed');
    } catch (error) {
      logger.error('Error polling for emails', { error });
      
      // If connection error, attempt to reconnect on next poll
      if (error.name === 'ConnectionError') {
        this.isConnected = false;
        this.connection = null;
      }
    } finally {
      this.isPolling = false;
    }
  }

  /**
   * Process a single email message
   * 
   * Extracts metadata and attachments, and publishes them to the message queue
   * 
   * @param message - The email message to process
   */
  private async processEmail(message: Message): Promise<void> {
    try {
      // Get the message ID from the header
      const headerPart = message.parts.find(part => part.which === 'HEADER');
      if (!headerPart) {
        throw createError('ProcessingError', 'Email header not found');
      }

      const messageId = headerPart.body['message-id']?.[0];
      if (!messageId) {
        throw createError('ProcessingError', 'Message ID not found in email header');
      }

      // Check if we've already processed this email
      if (this.processedEmails.has(messageId)) {
        logger.info('Skipping already processed email', { messageId });
        return;
      }

      logger.info('Processing email', { messageId });

      // Get the full message body
      const bodyPart = message.parts.find(part => part.which === '');
      if (!bodyPart) {
        throw createError('ProcessingError', 'Email body not found');
      }

      // Parse the email using mailparser
      const parsedEmail = await simpleParser(bodyPart.body);

      // Extract email metadata
      const metadata: IEmailMetadata = {
        messageId,
        from: parsedEmail.from?.text || '',
        to: parsedEmail.to?.text || '',
        subject: parsedEmail.subject || '',
        date: parsedEmail.date || new Date(),
        receivedDate: new Date()
      };

      logger.info('Extracted email metadata', { 
        messageId, 
        from: metadata.from,
        subject: metadata.subject
      });

      // Check if email has attachments
      if (!parsedEmail.attachments || parsedEmail.attachments.length === 0) {
        logger.info('Email has no attachments, skipping', { messageId });
        
        // Mark as processed even if no attachments
        this.markAsProcessed(messageId);
        
        // Mark as seen in the mailbox
        if (this.connection) {
          await this.connection.addFlags(message.attributes.uid, '\\Seen');
        }
        
        return;
      }

      // Process attachments
      const attachments: IEmailAttachment[] = [];
      
      for (const attachment of parsedEmail.attachments) {
        try {
          // Validate attachment (file type, size, etc.)
          const isValid = validateAttachment(attachment);
          if (!isValid) {
            logger.warn('Invalid attachment, skipping', { 
              messageId, 
              filename: attachment.filename 
            });
            continue;
          }

          // Scan attachment for viruses
          const scanResult = await this.virusScannerService.scanBuffer(attachment.content);
          if (!scanResult.isClean) {
            logger.warn('Virus detected in attachment, quarantining', { 
              messageId, 
              filename: attachment.filename,
              threat: scanResult.threatName 
            });
            
            // Quarantine the infected file
            await this.virusScannerService.quarantineBuffer(
              attachment.content, 
              attachment.filename || 'unknown_file',
              messageId
            );
            
            continue;
          }

          // Process the attachment
          const processedAttachment = await this.attachmentProcessorService.processAttachment({
            filename: attachment.filename || 'unknown_file',
            contentType: attachment.contentType,
            content: attachment.content,
            size: attachment.size || 0,
            contentDisposition: attachment.contentDisposition || 'attachment'
          });

          // Store attachment in S3
          const storagePath = await this.storageService.storeAttachment(
            processedAttachment.content,
            processedAttachment.filename,
            processedAttachment.contentType,
            metadata
          );

          // Add to attachments list
          attachments.push({
            filename: processedAttachment.filename,
            contentType: processedAttachment.contentType,
            size: processedAttachment.size,
            storagePath,
            metadata: processedAttachment.metadata
          });

          logger.info('Processed attachment', { 
            messageId, 
            filename: processedAttachment.filename,
            contentType: processedAttachment.contentType,
            size: processedAttachment.size
          });
        } catch (error) {
          logger.error('Error processing attachment', { 
            messageId, 
            filename: attachment.filename,
            error 
          });
          // Continue with other attachments even if one fails
        }
      }

      // If no valid attachments were processed, skip
      if (attachments.length === 0) {
        logger.info('No valid attachments found, skipping', { messageId });
        
        // Mark as processed
        this.markAsProcessed(messageId);
        
        // Mark as seen in the mailbox
        if (this.connection) {
          await this.connection.addFlags(message.attributes.uid, '\\Seen');
        }
        
        return;
      }

      // Create email message object
      const emailMessage: IEmailMessage = {
        metadata,
        attachments
      };

      // Publish to message queue
      await this.messageQueueService.publishEmailMessage(emailMessage);

      logger.info('Email processed and published to message queue', { 
        messageId,
        attachmentCount: attachments.length 
      });

      // Mark as processed
      this.markAsProcessed(messageId);

      // Mark as seen in the mailbox
      if (this.connection) {
        await this.connection.addFlags(message.attributes.uid, '\\Seen');
      }
    } catch (error) {
      logger.error('Error processing email', { 
        uid: message.attributes.uid,
        error 
      });
      // Don't rethrow, continue with other messages
    }
  }

  /**
   * Mark an email as processed
   * 
   * Adds the message ID to the processed emails map to prevent duplicate processing
   * 
   * @param messageId - The message ID to mark as processed
   */
  private markAsProcessed(messageId: string): void {
    this.processedEmails.set(messageId, {
      messageId,
      processedAt: new Date()
    });

    // Cleanup old processed emails (older than 7 days)
    this.cleanupProcessedEmails();
  }

  /**
   * Cleanup old processed emails
   * 
   * Removes message IDs from the processed emails map that are older than 7 days
   */
  private cleanupProcessedEmails(): void {
    const now = new Date();
    const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

    for (const [messageId, processedEmail] of this.processedEmails.entries()) {
      if (processedEmail.processedAt < sevenDaysAgo) {
        this.processedEmails.delete(messageId);
      }
    }
  }
}