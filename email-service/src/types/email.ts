import type { IDateValue } from './common';

// ----------------------------------------------------------------------

/**
 * Email sender or recipient information
 */
export interface IEmailParticipant {
  /** Full name of the email participant */
  name: string;
  /** Email address of the participant */
  email: string;
}

/**
 * Processing status for email messages and attachments
 */
export enum EmailProcessingStatus {
  /** Email has been received but not yet processed */
  RECEIVED = 'received',
  /** Email is currently being processed */
  PROCESSING = 'processing',
  /** Email has been successfully processed */
  PROCESSED = 'processed',
  /** Email processing has failed */
  FAILED = 'failed',
  /** Email has been quarantined due to security concerns */
  QUARANTINED = 'quarantined',
}

/**
 * Metadata for email messages
 */
export interface IEmailMetadata {
  /** Unique identifier for the email message */
  messageId: string;
  /** Email subject line */
  subject: string;
  /** Sender information */
  from: IEmailParticipant;
  /** Recipients information */
  to: IEmailParticipant[];
  /** Carbon copy recipients */
  cc?: IEmailParticipant[];
  /** Blind carbon copy recipients */
  bcc?: IEmailParticipant[];
  /** Date when the email was received */
  receivedDate: IDateValue;
  /** Date when the email was sent */
  sentDate: IDateValue;
  /** Current processing status */
  status: EmailProcessingStatus;
  /** Error message if processing failed */
  errorMessage?: string;
  /** Number of processing attempts */
  processingAttempts: number;
  /** Maximum number of processing attempts before giving up */
  maxProcessingAttempts: number;
  /** Priority level for processing (higher number = higher priority) */
  priority: number;
}

/**
 * Document classification confidence scores
 */
export interface IDocumentClassification {
  /** Predicted document type */
  documentType: string;
  /** Confidence score (0-1) for the classification */
  confidenceScore: number;
  /** Alternative document types with their confidence scores */
  alternatives?: Array<{
    documentType: string;
    confidenceScore: number;
  }>;
}

/**
 * Email attachment information
 */
export interface IEmailAttachment {
  /** Unique identifier for the attachment */
  id: string;
  /** Original filename of the attachment */
  name: string;
  /** Size of the attachment in bytes */
  size: number;
  /** MIME type of the attachment */
  contentType: string;
  /** Content ID for inline attachments */
  contentId?: string;
  /** Path to the attachment in temporary storage */
  tempPath: string;
  /** Path to the attachment in S3-compatible storage (after processing) */
  storagePath?: string;
  /** Document classification information (after processing) */
  classification?: IDocumentClassification;
  /** Current processing status */
  status: EmailProcessingStatus;
  /** Error message if processing failed */
  errorMessage?: string;
  /** Virus scan result (true = clean, false = infected) */
  isClean?: boolean;
  /** Date when the attachment was created */
  createdAt: IDateValue;
  /** Date when the attachment was last modified */
  modifiedAt: IDateValue;
  /** Checksum for file integrity verification */
  checksum: string;
  /** Metadata extracted from the attachment */
  metadata?: Record<string, unknown>;
}

/**
 * Complete email message with metadata and attachments
 */
export interface IEmailMessage {
  /** Email metadata */
  metadata: IEmailMetadata;
  /** Email body content (plain text) */
  textContent?: string;
  /** Email body content (HTML) */
  htmlContent?: string;
  /** Email attachments */
  attachments: IEmailAttachment[];
  /** Current processing status */
  status: EmailProcessingStatus;
  /** Date when processing started */
  processingStartedAt?: IDateValue;
  /** Date when processing completed */
  processingCompletedAt?: IDateValue;
  /** Processing duration in milliseconds */
  processingDuration?: number;
  /** Unique identifier for the application (if identified) */
  applicationId?: string;
  /** Tags for categorization and filtering */
  tags?: string[];
}

/**
 * Email processing result
 */
export interface IEmailProcessingResult {
  /** Success status of the processing operation */
  success: boolean;
  /** Email message that was processed */
  message: IEmailMessage;
  /** Error message if processing failed */
  error?: string;
  /** Detailed error information if processing failed */
  errorDetails?: Record<string, unknown>;
  /** Number of attachments successfully processed */
  processedAttachments: number;
  /** Number of attachments that failed processing */
  failedAttachments: number;
  /** Processing status */
  status: EmailProcessingStatus;
}

/**
 * Email search criteria for IMAP queries
 */
export interface IEmailSearchCriteria {
  /** Search for emails from a specific sender */
  from?: string;
  /** Search for emails to a specific recipient */
  to?: string;
  /** Search for emails with a specific subject */
  subject?: string;
  /** Search for emails received since a specific date */
  since?: Date;
  /** Search for emails received before a specific date */
  before?: Date;
  /** Search for emails with specific flags */
  flags?: string[];
  /** Search for emails with specific keywords */
  keywords?: string[];
  /** Search for emails with attachments */
  hasAttachments?: boolean;
  /** Custom IMAP search criteria */
  custom?: string[];
}