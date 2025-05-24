/**
 * Attachment Processor Service
 * 
 * This service handles the extraction and processing of email attachments, including
 * validation of file types, metadata extraction, and preparation for virus scanning
 * and storage. It is a critical component for the initial processing of application
 * documents in the MCA system.
 */

import { inject, injectable } from 'inversify';
import { promises as fs } from 'fs';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';
import { createHash } from 'crypto';
import * as mime from 'mime-types';

// Import types
import { IEmailAttachment, IEmailMessage } from '../types/email';
import { ILogger } from '../types/common';
import { IAppConfig } from '../types/config';
import { TYPES } from '../types/inversify-types';

// Import utilities
import { 
  validateFile, 
  isValidFileExtension, 
  isValidMimeType,
  formatFileSize,
  MAX_ATTACHMENT_SIZE
} from '../utils/validation';

// Import services
import { VirusScannerService } from './virus-scanner.service';

/**
 * Interface for attachment processing options
 */
export interface IAttachmentProcessingOptions {
  // Whether to scan attachments for viruses
  scanForViruses: boolean;
  
  // Whether to validate attachment types
  validateTypes: boolean;
  
  // Whether to extract metadata
  extractMetadata: boolean;
  
  // Maximum attachment size in bytes (defaults to MAX_ATTACHMENT_SIZE)
  maxSize?: number;
  
  // Temporary directory for attachment processing
  tempDir?: string;
}

/**
 * Interface for attachment processing result
 */
export interface IAttachmentProcessingResult {
  // Whether the processing was successful
  success: boolean;
  
  // Processed attachment with additional metadata
  attachment?: IEmailAttachment;
  
  // Error message if processing failed
  error?: string;
  
  // Error details if processing failed
  errorDetails?: Record<string, any>;
}

/**
 * Attachment Processor Service
 * 
 * Handles the extraction and processing of email attachments, including validation
 * of file types, metadata extraction, and preparation for virus scanning and storage.
 */
@injectable()
export class AttachmentProcessorService {
  // Default temporary directory for attachment processing
  private readonly DEFAULT_TEMP_DIR = path.join(process.cwd(), 'temp');
  
  // Default processing options
  private readonly DEFAULT_OPTIONS: IAttachmentProcessingOptions = {
    scanForViruses: true,
    validateTypes: true,
    extractMetadata: true,
    maxSize: MAX_ATTACHMENT_SIZE,
    tempDir: this.DEFAULT_TEMP_DIR
  };
  
  constructor(
    @inject(TYPES.Logger) private readonly logger: ILogger,
    @inject(TYPES.AppConfig) private readonly appConfig: IAppConfig,
    @inject(TYPES.VirusScannerService) private readonly virusScannerService: VirusScannerService
  ) {
    // Ensure temporary directory exists
    this.ensureTempDirectory();
  }
  
  /**
   * Ensure temporary directory exists
   */
  private async ensureTempDirectory(tempDir?: string): Promise<void> {
    const dir = tempDir || this.DEFAULT_OPTIONS.tempDir;
    
    try {
      await fs.mkdir(dir, { recursive: true });
      this.logger.info('Temporary directory created or verified', { path: dir });
    } catch (error) {
      this.logger.error('Failed to create temporary directory', {
        path: dir,
        error: error.message
      });
      throw new Error(`Failed to create temporary directory: ${error.message}`);
    }
  }
  
  /**
   * Process attachments from an email message
   * 
   * @param emailMessage - The email message containing attachments
   * @param options - Processing options
   * @returns Array of processing results for each attachment
   */
  public async processAttachments(
    emailMessage: IEmailMessage,
    options?: Partial<IAttachmentProcessingOptions>
  ): Promise<IAttachmentProcessingResult[]> {
    const processingOptions = { ...this.DEFAULT_OPTIONS, ...options };
    const results: IAttachmentProcessingResult[] = [];
    
    // Check if email has attachments
    if (!emailMessage.attachments || emailMessage.attachments.length === 0) {
      this.logger.info('No attachments found in email', {
        messageId: emailMessage.metadata.messageId
      });
      return results;
    }
    
    // Process each attachment
    for (const attachment of emailMessage.attachments) {
      try {
        const result = await this.processAttachment(attachment, emailMessage, processingOptions);
        results.push(result);
      } catch (error) {
        this.logger.error('Error processing attachment', {
          messageId: emailMessage.metadata.messageId,
          attachmentName: attachment.name,
          error: error.message
        });
        
        results.push({
          success: false,
          error: `Error processing attachment: ${error.message}`,
          errorDetails: { message: error.message, stack: error.stack }
        });
      }
    }
    
    return results;
  }
  
  /**
   * Process a single attachment
   * 
   * @param attachment - The email attachment to process
   * @param emailMessage - The parent email message
   * @param options - Processing options
   * @returns Processing result
   */
  public async processAttachment(
    attachment: IEmailAttachment,
    emailMessage: IEmailMessage,
    options: IAttachmentProcessingOptions
  ): Promise<IAttachmentProcessingResult> {
    this.logger.info('Processing attachment', {
      messageId: emailMessage.metadata.messageId,
      attachmentName: attachment.name,
      size: attachment.size
    });
    
    // Generate a unique ID for the attachment if not already present
    if (!attachment.id) {
      attachment.id = uuidv4();
    }
    
    // Add email message ID reference to the attachment
    attachment.emailId = emailMessage.metadata.messageId;
    
    // Validate attachment if required
    if (options.validateTypes) {
      const validationResult = this.validateAttachment(attachment, options.maxSize);
      
      if (!validationResult.success) {
        return validationResult;
      }
    }
    
    // Extract attachment to temporary file if content is provided
    if (attachment.content) {
      try {
        const tempFilePath = await this.extractAttachmentToFile(attachment, options.tempDir);
        attachment.path = tempFilePath;
      } catch (error) {
        return {
          success: false,
          error: `Failed to extract attachment to file: ${error.message}`,
          errorDetails: { message: error.message, stack: error.stack }
        };
      }
    }
    
    // Extract metadata if required
    if (options.extractMetadata) {
      try {
        await this.extractMetadata(attachment);
      } catch (error) {
        return {
          success: false,
          error: `Failed to extract attachment metadata: ${error.message}`,
          errorDetails: { message: error.message, stack: error.stack }
        };
      }
    }
    
    // Scan for viruses if required and virus scanner is initialized
    if (options.scanForViruses && this.virusScannerService.isInitialized()) {
      try {
        const scanResult = await this.virusScannerService.scanAttachment(attachment);
        
        if (scanResult.isInfected) {
          return {
            success: false,
            attachment,
            error: 'Attachment contains a virus or malware',
            errorDetails: { viruses: scanResult.viruses }
          };
        }
        
        // Update scan status
        attachment.scanStatus = 'clean';
      } catch (error) {
        this.logger.warn('Virus scanning failed, proceeding without scan', {
          attachmentId: attachment.id,
          error: error.message
        });
        
        // Mark as pending for later scanning
        attachment.scanStatus = 'pending';
      }
    } else {
      // Mark as pending for later scanning
      attachment.scanStatus = 'pending';
    }
    
    // Update processing status
    attachment.processingStatus = 'completed';
    attachment.processedAt = Date.now();
    
    return {
      success: true,
      attachment
    };
  }
  
  /**
   * Validate an attachment
   * 
   * @param attachment - The attachment to validate
   * @param maxSize - Maximum allowed size in bytes
   * @returns Validation result
   */
  private validateAttachment(
    attachment: IEmailAttachment,
    maxSize: number = MAX_ATTACHMENT_SIZE
  ): IAttachmentProcessingResult {
    // Check if attachment has required properties
    if (!attachment.name || !attachment.size) {
      return {
        success: false,
        error: 'Attachment missing required properties (name or size)',
        errorDetails: { attachment }
      };
    }
    
    // Determine content type if not provided
    if (!attachment.type) {
      attachment.type = mime.lookup(attachment.name) || 'application/octet-stream';
    }
    
    // Validate file using utility function
    const validation = validateFile(attachment.name, attachment.size, attachment.type);
    
    if (!validation.valid) {
      return {
        success: false,
        error: validation.error || 'Invalid attachment',
        errorDetails: { validation }
      };
    }
    
    return { success: true };
  }
  
  /**
   * Extract attachment content to a temporary file
   * 
   * @param attachment - The attachment to extract
   * @param tempDir - Temporary directory path
   * @returns Path to the extracted file
   */
  private async extractAttachmentToFile(
    attachment: IEmailAttachment,
    tempDir?: string
  ): Promise<string> {
    if (!attachment.content) {
      throw new Error('Attachment content is required for extraction');
    }
    
    const dir = tempDir || this.DEFAULT_OPTIONS.tempDir;
    
    // Ensure temp directory exists
    await this.ensureTempDirectory(dir);
    
    // Generate a unique filename to prevent collisions
    const uniquePrefix = createHash('md5')
      .update(`${attachment.emailId}-${attachment.name}-${Date.now()}`)
      .digest('hex');
      
    // Clean the original filename to remove potentially problematic characters
    const cleanFilename = attachment.name.replace(/[^a-zA-Z0-9._-]/g, '_');
    
    // Create the full temporary file path
    const tempFilePath = path.join(dir, `${uniquePrefix}-${cleanFilename}`);
    
    // Write the attachment content to the temporary file
    await fs.writeFile(tempFilePath, attachment.content);
    
    this.logger.info('Attachment extracted to temporary file', {
      attachmentId: attachment.id,
      tempFilePath
    });
    
    return tempFilePath;
  }
  
  /**
   * Extract metadata from an attachment
   * 
   * @param attachment - The attachment to extract metadata from
   */
  private async extractMetadata(attachment: IEmailAttachment): Promise<void> {
    if (!attachment.path) {
      throw new Error('Attachment path is required for metadata extraction');
    }
    
    try {
      // Get file stats
      const stats = await fs.stat(attachment.path);
      
      // Update attachment with file stats
      attachment.size = stats.size;
      attachment.createdAt = stats.birthtime.getTime();
      
      // Calculate MD5 hash of the file for integrity verification
      const fileBuffer = await fs.readFile(attachment.path);
      const md5Hash = createHash('md5').update(fileBuffer).digest('hex');
      
      // Add metadata
      attachment.metadata = attachment.metadata || {};
      attachment.metadata.md5Hash = md5Hash;
      attachment.metadata.fileStats = {
        size: stats.size,
        created: stats.birthtime.toISOString(),
        modified: stats.mtime.toISOString(),
        accessed: stats.atime.toISOString()
      };
      
      // Determine MIME type if not already set or if it's generic
      if (!attachment.type || attachment.type === 'application/octet-stream') {
        const detectedType = mime.lookup(attachment.path) || 'application/octet-stream';
        attachment.type = detectedType;
      }
      
      this.logger.info('Attachment metadata extracted', {
        attachmentId: attachment.id,
        size: formatFileSize(attachment.size),
        type: attachment.type,
        md5Hash
      });
    } catch (error) {
      this.logger.error('Failed to extract attachment metadata', {
        attachmentId: attachment.id,
        path: attachment.path,
        error: error.message
      });
      
      throw new Error(`Metadata extraction failed: ${error.message}`);
    }
  }
  
  /**
   * Clean up temporary files for an attachment
   * 
   * @param attachment - The attachment to clean up
   */
  public async cleanupAttachment(attachment: IEmailAttachment): Promise<void> {
    if (attachment.path) {
      try {
        await fs.unlink(attachment.path);
        
        this.logger.info('Temporary attachment file removed', {
          attachmentId: attachment.id,
          path: attachment.path
        });
      } catch (error) {
        this.logger.warn('Failed to remove temporary attachment file', {
          attachmentId: attachment.id,
          path: attachment.path,
          error: error.message
        });
      }
    }
  }
  
  /**
   * Clean up all temporary files for multiple attachments
   * 
   * @param attachments - The attachments to clean up
   */
  public async cleanupAttachments(attachments: IEmailAttachment[]): Promise<void> {
    for (const attachment of attachments) {
      await this.cleanupAttachment(attachment);
    }
  }
  
  /**
   * Prepare attachments for storage
   * This method prepares attachments for storage in S3 by ensuring they have
   * all required metadata and have been properly processed
   * 
   * @param attachments - The attachments to prepare
   * @returns Prepared attachments ready for storage
   */
  public prepareAttachmentsForStorage(attachments: IEmailAttachment[]): IEmailAttachment[] {
    return attachments.map(attachment => {
      // Ensure attachment has all required fields
      if (!attachment.id) {
        attachment.id = uuidv4();
      }
      
      if (!attachment.createdAt) {
        attachment.createdAt = Date.now();
      }
      
      // Set storage metadata
      attachment.metadata = attachment.metadata || {};
      attachment.metadata.storageClass = 'STANDARD';
      attachment.metadata.contentEncoding = 'identity';
      attachment.metadata.contentDisposition = `attachment; filename="${attachment.name}"`;
      
      return attachment;
    });
  }
  
  /**
   * Extract attachments from an email message
   * This is a utility method that extracts attachment objects from raw email data
   * 
   * @param emailData - Raw email data
   * @returns Extracted email attachments
   */
  public extractAttachmentsFromEmail(emailData: any): IEmailAttachment[] {
    // This is a placeholder implementation
    // In a real implementation, this would parse the raw email data
    // and extract attachments using a library like mailparser
    
    if (!emailData || !emailData.attachments || !Array.isArray(emailData.attachments)) {
      return [];
    }
    
    return emailData.attachments.map((rawAttachment: any) => {
      const attachment: IEmailAttachment = {
        id: uuidv4(),
        name: rawAttachment.filename || 'unknown',
        size: rawAttachment.size || 0,
        type: rawAttachment.contentType || mime.lookup(rawAttachment.filename) || 'application/octet-stream',
        content: rawAttachment.content,
        contentId: rawAttachment.contentId,
        createdAt: Date.now(),
        emailId: emailData.messageId,
        isValid: false, // Will be validated during processing
        scanStatus: 'pending',
        processingStatus: 'pending'
      };
      
      return attachment;
    });
  }
}