/**
 * Attachment Processor Service
 * 
 * Handles the extraction and processing of email attachments, including validation of file types,
 * metadata extraction, and preparation for virus scanning and storage. This service is critical
 * for the initial processing of application documents in the MCA system.
 * 
 * Key responsibilities:
 * - Extract attachments from email messages
 * - Validate attachment types (PDF, TIFF, PNG, JPEG)
 * - Extract attachment metadata (filename, size, content type)
 * - Prepare attachments for virus scanning
 * - Handle errors for corrupted or unsupported attachments
 */

import { Attachment } from 'nodemailer/lib/mailer';
import { simpleParser, ParsedMail } from 'mailparser';
import { createHash } from 'crypto';
import { IEmailAttachment, IEmailMessage, EmailProcessingStatus } from '../types/email';
import { FileMetadata, processAttachment, prepareForVirusScan, isValidDocumentType, formatFileSize } from '../utils/file';
import { validateAttachment } from '../utils/validation';
import { createServiceError } from '../utils/error';
import { logger } from '../utils/logger';

/**
 * Configuration options for the AttachmentProcessor
 */
export interface AttachmentProcessorOptions {
  /** Maximum size of attachments to process (in bytes) */
  maxAttachmentSize?: number;
  /** Whether to skip virus scanning (not recommended for production) */
  skipVirusScan?: boolean;
  /** Temporary directory for attachment processing */
  tempDir?: string;
  /** Whether to extract inline attachments */
  extractInlineAttachments?: boolean;
  /** Whether to extract embedded images */
  extractEmbeddedImages?: boolean;
}

/**
 * Result of attachment processing
 */
export interface AttachmentProcessingResult {
  /** Processed attachments */
  attachments: IEmailAttachment[];
  /** Number of successful attachments */
  successCount: number;
  /** Number of failed attachments */
  failedCount: number;
  /** Processing errors, if any */
  errors: Error[];
}

/**
 * Service for processing email attachments
 */
export class AttachmentProcessor {
  private options: Required<AttachmentProcessorOptions>;

  /**
   * Creates a new AttachmentProcessor instance
   * @param options - Configuration options
   */
  constructor(options: AttachmentProcessorOptions = {}) {
    // Set default options
    this.options = {
      maxAttachmentSize: 25 * 1024 * 1024, // 25MB default
      skipVirusScan: process.env.NODE_ENV === 'development', // Skip in dev only
      tempDir: undefined, // Will be created as needed
      extractInlineAttachments: true,
      extractEmbeddedImages: false, // Don't extract embedded images by default
      ...options
    };

    logger.info('AttachmentProcessor initialized', { options: this.options });
  }

  /**
   * Processes attachments from a raw email message
   * @param rawEmail - Raw email content as a Buffer or string
   * @returns Promise resolving to the attachment processing result
   */
  public async processEmailAttachments(rawEmail: Buffer | string): Promise<AttachmentProcessingResult> {
    try {
      // Parse the raw email
      const parsedEmail = await simpleParser(rawEmail);
      
      // Extract message ID or generate one if not present
      const messageId = parsedEmail.messageId || this.generateMessageId(parsedEmail);
      
      logger.info('Processing attachments from email', { 
        messageId, 
        subject: parsedEmail.subject,
        attachmentCount: parsedEmail.attachments?.length || 0 
      });

      return this.processAttachmentsFromParsedEmail(parsedEmail, messageId);
    } catch (error) {
      logger.error('Failed to parse email', { error });
      throw createServiceError('Failed to parse email', error as Error);
    }
  }

  /**
   * Processes attachments from a parsed email message
   * @param parsedEmail - Parsed email message
   * @param messageId - Email message ID
   * @returns Promise resolving to the attachment processing result
   */
  public async processAttachmentsFromParsedEmail(
    parsedEmail: ParsedMail, 
    messageId: string
  ): Promise<AttachmentProcessingResult> {
    const result: AttachmentProcessingResult = {
      attachments: [],
      successCount: 0,
      failedCount: 0,
      errors: []
    };

    // Check if email has attachments
    if (!parsedEmail.attachments || parsedEmail.attachments.length === 0) {
      logger.info('No attachments found in email', { messageId });
      return result;
    }

    // Get sender information
    const senderEmail = parsedEmail.from?.value[0]?.address || '';
    const senderName = parsedEmail.from?.value[0]?.name || '';
    
    // Process each attachment
    for (const attachment of parsedEmail.attachments) {
      try {
        // Skip inline attachments if configured to do so
        if (attachment.contentDisposition === 'inline' && !this.options.extractInlineAttachments) {
          logger.debug('Skipping inline attachment', { 
            filename: attachment.filename, 
            contentId: attachment.contentId 
          });
          continue;
        }

        // Skip embedded images if configured to do so
        if (
          attachment.contentType.startsWith('image/') && 
          attachment.contentDisposition === 'inline' && 
          !this.options.extractEmbeddedImages
        ) {
          logger.debug('Skipping embedded image', { 
            filename: attachment.filename, 
            contentType: attachment.contentType 
          });
          continue;
        }

        // Process the attachment
        const processedAttachment = await this.processAttachment(
          attachment, 
          messageId, 
          senderEmail,
          senderName
        );
        
        result.attachments.push(processedAttachment);
        result.successCount++;
        
        logger.info('Successfully processed attachment', { 
          filename: processedAttachment.name,
          size: formatFileSize(processedAttachment.size),
          contentType: processedAttachment.contentType,
          messageId
        });
      } catch (error) {
        result.failedCount++;
        result.errors.push(error as Error);
        
        logger.error('Failed to process attachment', { 
          filename: attachment.filename,
          error: (error as Error).message,
          messageId
        });
      }
    }

    logger.info('Completed processing email attachments', { 
      messageId,
      successCount: result.successCount,
      failedCount: result.failedCount,
      totalAttachments: result.attachments.length
    });

    return result;
  }

  /**
   * Processes a single attachment
   * @param attachment - Email attachment
   * @param messageId - Email message ID
   * @param senderEmail - Sender email address
   * @param senderName - Sender name
   * @returns Promise resolving to the processed email attachment
   */
  private async processAttachment(
    attachment: any, 
    messageId: string,
    senderEmail: string,
    senderName: string
  ): Promise<IEmailAttachment> {
    // Validate attachment has required properties
    if (!attachment.content || !attachment.filename) {
      throw new Error('Invalid attachment: missing content or filename');
    }

    // Check attachment size
    if (attachment.size > this.options.maxAttachmentSize) {
      throw new Error(
        `Attachment size exceeds maximum allowed size of ${formatFileSize(this.options.maxAttachmentSize)}`
      );
    }

    // Get content type or default to application/octet-stream
    const contentType = attachment.contentType || 'application/octet-stream';
    
    // Validate document type
    if (!isValidDocumentType(contentType)) {
      throw new Error(`Unsupported document type: ${contentType}`);
    }

    // Generate a unique ID for the attachment
    const id = this.generateAttachmentId(attachment, messageId);
    
    // Get current timestamp
    const now = new Date();
    
    // Create file metadata using utility function
    const fileMetadata = await processAttachment(
      attachment.content, 
      attachment.filename,
      {
        sourceMessageId: messageId,
        sourceSender: senderEmail,
        skipVirusScan: this.options.skipVirusScan
      }
    );

    // Create the email attachment object
    const emailAttachment: IEmailAttachment = {
      id,
      name: attachment.filename,
      size: attachment.size,
      contentType,
      contentId: attachment.contentId,
      tempPath: fileMetadata.path || '',
      status: EmailProcessingStatus.PROCESSED,
      createdAt: now.toISOString(),
      modifiedAt: now.toISOString(),
      checksum: fileMetadata.contentHash || '',
      metadata: {
        originalFilename: attachment.filename,
        contentDisposition: attachment.contentDisposition || 'attachment',
        senderEmail,
        senderName,
        messageId,
        receivedDate: now.toISOString()
      }
    };

    // If virus scanning was performed, update the status
    if (fileMetadata.virusScanned) {
      emailAttachment.isClean = fileMetadata.isSafe;
      
      // If the file is not safe, update the status
      if (!fileMetadata.isSafe) {
        emailAttachment.status = EmailProcessingStatus.QUARANTINED;
        emailAttachment.errorMessage = 'Virus detected in attachment';
      }
    }

    return emailAttachment;
  }

  /**
   * Prepares attachments for virus scanning
   * @param attachments - Array of email attachments
   * @returns Promise resolving to an array of attachments with scan results
   */
  public async prepareForVirusScan(
    attachments: IEmailAttachment[]
  ): Promise<{ attachments: IEmailAttachment[]; cleanupFunctions: Array<() => Promise<void>> }> {
    const cleanupFunctions: Array<() => Promise<void>> = [];
    const results: IEmailAttachment[] = [];

    for (const attachment of attachments) {
      try {
        // Skip attachments that have already been scanned
        if (attachment.isClean !== undefined) {
          results.push(attachment);
          continue;
        }

        // Get the attachment content (this would come from tempPath in a real implementation)
        // For this example, we're assuming the content is available
        const content = Buffer.from(''); // Placeholder - in real implementation, read from tempPath
        
        // Prepare for virus scanning
        const { filePath, cleanup } = await prepareForVirusScan(content, attachment.name);
        
        // Add cleanup function to the list
        cleanupFunctions.push(cleanup);
        
        // Update attachment with scan path
        const updatedAttachment = { 
          ...attachment,
          tempPath: filePath,
          status: EmailProcessingStatus.PROCESSING
        };
        
        results.push(updatedAttachment);
        
        logger.debug('Prepared attachment for virus scanning', { 
          id: attachment.id, 
          filename: attachment.name,
          scanPath: filePath
        });
      } catch (error) {
        logger.error('Failed to prepare attachment for virus scanning', { 
          id: attachment.id,
          filename: attachment.name,
          error: (error as Error).message
        });
        
        // Mark the attachment as failed
        results.push({
          ...attachment,
          status: EmailProcessingStatus.FAILED,
          errorMessage: `Failed to prepare for virus scanning: ${(error as Error).message}`
        });
      }
    }

    return { attachments: results, cleanupFunctions };
  }

  /**
   * Validates attachments against supported types and size limits
   * @param attachments - Array of email attachments to validate
   * @returns Object containing valid and invalid attachments
   */
  public validateAttachments(
    attachments: IEmailAttachment[]
  ): { valid: IEmailAttachment[]; invalid: Array<{ attachment: IEmailAttachment; reason: string }> } {
    const valid: IEmailAttachment[] = [];
    const invalid: Array<{ attachment: IEmailAttachment; reason: string }> = [];

    for (const attachment of attachments) {
      const validation = validateAttachment(attachment);
      
      if (validation.isValid) {
        valid.push(attachment);
      } else {
        invalid.push({
          attachment,
          reason: validation.reason || 'Unknown validation failure'
        });
        
        logger.warn('Invalid attachment', { 
          id: attachment.id,
          filename: attachment.name,
          reason: validation.reason
        });
      }
    }

    return { valid, invalid };
  }

  /**
   * Extracts metadata from attachments
   * @param attachments - Array of email attachments
   * @returns Array of attachments with extracted metadata
   */
  public extractMetadata(attachments: IEmailAttachment[]): IEmailAttachment[] {
    return attachments.map(attachment => {
      // Extract additional metadata based on file type
      const additionalMetadata: Record<string, unknown> = {};
      
      // Extract metadata based on content type
      if (attachment.contentType === 'application/pdf') {
        // PDF-specific metadata would be extracted here
        // This is a placeholder for actual PDF metadata extraction
        additionalMetadata.pdfVersion = '1.7'; // Example
        additionalMetadata.pageCount = 0; // Example
      } else if (attachment.contentType.startsWith('image/')) {
        // Image-specific metadata would be extracted here
        // This is a placeholder for actual image metadata extraction
        additionalMetadata.imageWidth = 0; // Example
        additionalMetadata.imageHeight = 0; // Example
      }
      
      // Merge with existing metadata
      return {
        ...attachment,
        metadata: {
          ...attachment.metadata,
          ...additionalMetadata,
          extractedAt: new Date().toISOString()
        }
      };
    });
  }

  /**
   * Generates a unique ID for an attachment
   * @param attachment - Email attachment
   * @param messageId - Email message ID
   * @returns Unique attachment ID
   */
  private generateAttachmentId(attachment: any, messageId: string): string {
    const timestamp = Date.now();
    const hash = createHash('md5')
      .update(messageId)
      .update(attachment.filename || '')
      .update(attachment.contentId || '')
      .update(timestamp.toString())
      .digest('hex');
    
    return `att_${hash}`;
  }

  /**
   * Generates a message ID if one is not present in the email
   * @param parsedEmail - Parsed email message
   * @returns Generated message ID
   */
  private generateMessageId(parsedEmail: ParsedMail): string {
    const timestamp = Date.now();
    const subject = parsedEmail.subject || 'no-subject';
    const sender = parsedEmail.from?.value[0]?.address || 'unknown-sender';
    
    const hash = createHash('md5')
      .update(subject)
      .update(sender)
      .update(timestamp.toString())
      .digest('hex');
    
    return `generated-${hash}@dollarfunding.com`;
  }
}

/**
 * Creates and exports a singleton instance of the AttachmentProcessor
 */
export const attachmentProcessor = new AttachmentProcessor();