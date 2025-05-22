import type { IDateValue } from './common';

// ----------------------------------------------------------------------

/**
 * Interface representing an email sender or recipient
 * Used for tracking the source and destination of email messages
 */
export interface IEmailSender {
  name: string;          // Display name of the sender/recipient
  email: string;         // Email address of the sender/recipient
  domain?: string;       // Domain portion of the email address (for filtering)
}

/**
 * Interface representing metadata about an email message
 * Contains essential information about the email without the content or attachments
 */
export interface IEmailMetadata {
  messageId: string;     // Unique identifier for the email message
  subject: string;       // Subject line of the email
  from: IEmailSender;    // Sender information
  to: IEmailSender[];    // List of recipients
  cc?: IEmailSender[];   // Carbon copy recipients (optional)
  receivedAt: IDateValue; // Timestamp when the email was received
  processedAt?: IDateValue; // Timestamp when the email was processed
  folderPath: string;    // IMAP folder path where the email is stored
  isProcessed: boolean;  // Flag indicating if the email has been processed
  processingStatus?: 'pending' | 'processing' | 'completed' | 'failed'; // Current processing status
  processingErrors?: string[]; // List of errors encountered during processing
}

/**
 * Interface representing an email attachment
 * Adapted from IMailAttachment but specialized for document processing needs
 */
export interface IEmailAttachment {
  id: string;            // Unique identifier for the attachment
  name: string;          // Original filename of the attachment
  size: number;          // Size of the attachment in bytes
  type: string;          // MIME type of the attachment
  contentId?: string;    // Content ID for inline attachments
  content?: Buffer;      // Binary content of the attachment
  storagePath?: string;  // Path where the attachment is stored in S3
  createdAt: IDateValue; // Timestamp when the attachment was created
  processedAt?: IDateValue; // Timestamp when the attachment was processed
  
  // Document processing specific fields
  documentType?: string; // Classified document type (loan application, tax return, etc.)
  classificationConfidence?: number; // Confidence score of document classification (0-1)
  isValid?: boolean;     // Flag indicating if the attachment is a valid document
  scanStatus?: 'pending' | 'scanning' | 'clean' | 'infected'; // Virus scan status
  processingStatus?: 'pending' | 'processing' | 'completed' | 'failed'; // Processing status
  processingErrors?: string[]; // List of errors encountered during processing
}

/**
 * Interface representing a complete email message with metadata and attachments
 * Used for processing incoming emails in the Email Service
 */
export interface IEmailMessage {
  metadata: IEmailMetadata; // Email metadata
  body?: string;         // Plain text body of the email (if available)
  htmlBody?: string;     // HTML body of the email (if available)
  attachments: IEmailAttachment[]; // List of attachments
  
  // Processing information
  hasAttachments: boolean; // Flag indicating if the email has attachments
  isValid: boolean;      // Flag indicating if the email is valid for processing
  isProcessed: boolean;  // Flag indicating if the email has been processed
  processingStatus: 'pending' | 'processing' | 'completed' | 'failed'; // Current processing status
  processingErrors?: string[]; // List of errors encountered during processing
  processingStartedAt?: IDateValue; // Timestamp when processing started
  processingCompletedAt?: IDateValue; // Timestamp when processing completed
}

/**
 * Interface representing a message to be published to RabbitMQ
 * Contains document information and routing details
 */
export interface IEmailDocumentMessage {
  messageId: string;     // Unique identifier for the message
  emailMessageId: string; // Reference to the original email message ID
  documentType: string;  // Classified document type
  sender: IEmailSender;  // Original sender information
  subject: string;       // Original email subject
  receivedAt: IDateValue; // Timestamp when the email was received
  attachment: {
    id: string;          // Attachment ID
    name: string;        // Original filename
    size: number;        // Size in bytes
    type: string;        // MIME type
    storagePath: string; // S3 storage path
    classificationConfidence?: number; // Confidence score (0-1)
  };
  metadata: Record<string, any>; // Additional metadata for processing
  createdAt: IDateValue; // Timestamp when the message was created
}

/**
 * Interface representing IMAP connection configuration
 * Used for connecting to email servers
 */
export interface IIMAPConfig {
  host: string;          // IMAP server hostname
  port: number;          // IMAP server port
  user: string;          // Username for authentication
  password: string;      // Password for authentication
  tls: boolean;          // Whether to use TLS
  tlsOptions?: Record<string, any>; // TLS connection options
  authTimeout?: number;  // Authentication timeout in milliseconds
  keepalive?: boolean;   // Whether to keep the connection alive
  mailbox?: string;      // Default mailbox to open
  searchFilter?: string[]; // IMAP search criteria
  markSeen?: boolean;    // Whether to mark emails as seen when fetched
}

/**
 * Interface representing email monitoring configuration
 * Used for configuring the email monitoring service
 */
export interface IEmailMonitoringConfig {
  enabled: boolean;      // Whether email monitoring is enabled
  pollingInterval: number; // Polling interval in milliseconds
  maxConcurrent: number; // Maximum number of concurrent email processing
  maxRetries: number;    // Maximum number of retries for failed processing
  retryDelay: number;    // Delay between retries in milliseconds
  folders: string[];     // List of folders to monitor
  allowedDomains?: string[]; // List of allowed sender domains (if any)
  allowedEmailAddresses?: string[]; // List of allowed sender email addresses (if any)
}