/**
 * @file storage.service.ts
 * @description Provides functionality for storing email attachments in S3-compatible storage with encryption.
 * This service ensures that documents are securely stored and accessible for processing by other services.
 */

import {
  S3Client,
  PutObjectCommand,
  GetObjectCommand,
  DeleteObjectCommand,
  HeadObjectCommand,
  ListObjectsV2Command,
  S3ServiceException,
  NotFound,
} from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import { createHash } from 'crypto';
import { Logger } from 'winston';

import {
  IS3Config,
  IStorageOptions,
  IStorageResult,
  ISignedUrlOptions,
  IStorageService,
  IDocumentMetadata,
} from '../types/storage';

/**
 * Default storage options with AES-256 encryption
 */
const DEFAULT_STORAGE_OPTIONS: IStorageOptions = {
  encryption: 'AES-256',
  contentType: 'application/octet-stream',
  acl: 'private',
  cacheControl: 'private, max-age=0, no-cache',
};

/**
 * Default retry configuration
 */
const DEFAULT_RETRY_CONFIG = {
  maxRetries: 3,
  initialDelayMs: 100,
  maxDelayMs: 5000,
  backoffFactor: 2,
};

/**
 * Implementation of the Storage Service for S3-compatible storage
 * Provides functionality for storing email attachments with encryption
 */
export class StorageService implements IStorageService {
  private s3Client: S3Client;
  private logger: Logger;
  private retryConfig: {
    maxRetries: number;
    initialDelayMs: number;
    maxDelayMs: number;
    backoffFactor: number;
  };

  /**
   * Creates a new instance of the StorageService
   * @param config S3 configuration
   * @param logger Winston logger instance
   * @param retryConfig Optional retry configuration
   */
  constructor(
    private readonly config: IS3Config,
    logger: Logger,
    retryConfig?: {
      maxRetries?: number;
      initialDelayMs?: number;
      maxDelayMs?: number;
      backoffFactor?: number;
    }
  ) {
    this.logger = logger.child({ service: 'StorageService' });
    this.retryConfig = {
      maxRetries: retryConfig?.maxRetries ?? DEFAULT_RETRY_CONFIG.maxRetries,
      initialDelayMs: retryConfig?.initialDelayMs ?? DEFAULT_RETRY_CONFIG.initialDelayMs,
      maxDelayMs: retryConfig?.maxDelayMs ?? DEFAULT_RETRY_CONFIG.maxDelayMs,
      backoffFactor: retryConfig?.backoffFactor ?? DEFAULT_RETRY_CONFIG.backoffFactor,
    };

    this.s3Client = new S3Client({
      endpoint: this.config.endpoint,
      region: this.config.region,
      credentials: {
        accessKeyId: this.config.credentials.accessKeyId,
        secretAccessKey: this.config.credentials.secretAccessKey,
        sessionToken: this.config.credentials.sessionToken,
      },
      forcePathStyle: this.config.forcePathStyle ?? true,
      maxAttempts: this.config.maxRetries ?? this.retryConfig.maxRetries,
      requestHandler: {
        connectionTimeout: this.config.connectionTimeout ?? 5000,
        socketTimeout: this.config.socketTimeout ?? 60000,
      } as any, // Type casting due to AWS SDK types mismatch
    });

    this.logger.info('Storage service initialized', {
      endpoint: this.config.endpoint,
      region: this.config.region,
      forcePathStyle: this.config.forcePathStyle,
    });
  }

  /**
   * Uploads a file to S3 with AES-256 encryption
   * @param bucket S3 bucket name
   * @param key Object key (path in the bucket)
   * @param body File content as Buffer
   * @param options Storage options
   * @returns Promise resolving to storage operation result
   */
  async uploadFile(
    bucket: string,
    key: string,
    body: Buffer,
    options?: IStorageOptions
  ): Promise<IStorageResult> {
    const mergedOptions = { ...DEFAULT_STORAGE_OPTIONS, ...options };
    const fileHash = this.calculateHash(body);
    
    try {
      this.logger.debug('Uploading file to S3', {
        bucket,
        key,
        size: body.length,
        contentType: mergedOptions.contentType,
        encryption: mergedOptions.encryption,
      });

      // Ensure we're using AES-256 encryption
      if (mergedOptions.encryption !== 'AES-256') {
        this.logger.warn('Encryption algorithm is not AES-256, forcing AES-256 encryption', {
          requestedEncryption: mergedOptions.encryption,
          appliedEncryption: 'AES-256',
        });
        mergedOptions.encryption = 'AES-256';
      }

      // Prepare metadata
      const metadata = {
        ...mergedOptions.metadata,
        'content-sha256': fileHash,
      };

      // Execute the upload with retries
      const result = await this.executeWithRetry(async () => {
        const command = new PutObjectCommand({
          Bucket: bucket,
          Key: key,
          Body: body,
          ContentType: mergedOptions.contentType,
          CacheControl: mergedOptions.cacheControl,
          ContentDisposition: mergedOptions.contentDisposition,
          ServerSideEncryption: mergedOptions.encryption,
          Metadata: metadata,
          ACL: mergedOptions.acl,
          Tagging: mergedOptions.tags
            ? Object.entries(mergedOptions.tags)
                .map(([key, value]) => `${key}=${value}`)
                .join('&')
            : undefined,
        });

        const response = await this.s3Client.send(command);

        return {
          success: true,
          key,
          etag: response.ETag?.replace(/"/g, ''), // Remove quotes from ETag
          versionId: response.VersionId,
          url: `${this.config.endpoint}/${bucket}/${key}`,
        };
      });

      this.logger.info('File uploaded successfully', {
        bucket,
        key,
        etag: result.etag,
        versionId: result.versionId,
      });

      return result;
    } catch (error) {
      this.logger.error('Failed to upload file to S3', {
        bucket,
        key,
        error: this.formatError(error),
        size: body.length,
      });

      return {
        success: false,
        error: this.formatError(error),
        message: 'Failed to upload file to S3',
      };
    }
  }

  /**
   * Downloads a file from S3
   * @param bucket S3 bucket name
   * @param key Object key (path in the bucket)
   * @returns Promise resolving to file content as Buffer
   */
  async downloadFile(bucket: string, key: string): Promise<Buffer> {
    try {
      this.logger.debug('Downloading file from S3', { bucket, key });

      const result = await this.executeWithRetry(async () => {
        const command = new GetObjectCommand({
          Bucket: bucket,
          Key: key,
        });

        const response = await this.s3Client.send(command);
        
        if (!response.Body) {
          throw new Error('Empty response body');
        }

        // Convert stream to buffer
        const chunks: Uint8Array[] = [];
        for await (const chunk of response.Body as any) {
          chunks.push(chunk);
        }
        
        return Buffer.concat(chunks);
      });

      this.logger.info('File downloaded successfully', {
        bucket,
        key,
        size: result.length,
      });

      return result;
    } catch (error) {
      this.logger.error('Failed to download file from S3', {
        bucket,
        key,
        error: this.formatError(error),
      });

      throw new Error(`Failed to download file from S3: ${this.formatError(error)}`);
    }
  }

  /**
   * Generates a signed URL for temporary access to a file
   * @param bucket S3 bucket name
   * @param key Object key (path in the bucket)
   * @param options Signed URL options
   * @returns Promise resolving to signed URL
   */
  async getSignedUrl(bucket: string, key: string, options: ISignedUrlOptions): Promise<string> {
    try {
      this.logger.debug('Generating signed URL', {
        bucket,
        key,
        expiresIn: options.expiresIn,
        method: options.method || 'GET',
      });

      const command = options.method === 'PUT'
        ? new PutObjectCommand({
            Bucket: bucket,
            Key: key,
            ContentType: options.contentType,
            ServerSideEncryption: 'AES-256', // Always enforce encryption
          })
        : new GetObjectCommand({
            Bucket: bucket,
            Key: key,
            ResponseContentType: options.responseContentType,
            ResponseContentDisposition: options.responseContentDisposition,
          });

      const url = await getSignedUrl(this.s3Client, command, {
        expiresIn: options.expiresIn,
      });

      this.logger.info('Signed URL generated successfully', {
        bucket,
        key,
        expiresIn: options.expiresIn,
        method: options.method || 'GET',
      });

      return url;
    } catch (error) {
      this.logger.error('Failed to generate signed URL', {
        bucket,
        key,
        error: this.formatError(error),
      });

      throw new Error(`Failed to generate signed URL: ${this.formatError(error)}`);
    }
  }

  /**
   * Deletes a file from S3
   * @param bucket S3 bucket name
   * @param key Object key (path in the bucket)
   * @returns Promise resolving to storage operation result
   */
  async deleteFile(bucket: string, key: string): Promise<IStorageResult> {
    try {
      this.logger.debug('Deleting file from S3', { bucket, key });

      const result = await this.executeWithRetry(async () => {
        const command = new DeleteObjectCommand({
          Bucket: bucket,
          Key: key,
        });

        const response = await this.s3Client.send(command);

        return {
          success: true,
          key,
          versionId: response.VersionId,
        };
      });

      this.logger.info('File deleted successfully', {
        bucket,
        key,
        versionId: result.versionId,
      });

      return result;
    } catch (error) {
      this.logger.error('Failed to delete file from S3', {
        bucket,
        key,
        error: this.formatError(error),
      });

      return {
        success: false,
        error: this.formatError(error),
        message: 'Failed to delete file from S3',
      };
    }
  }

  /**
   * Checks if a file exists in S3
   * @param bucket S3 bucket name
   * @param key Object key (path in the bucket)
   * @returns Promise resolving to boolean indicating if file exists
   */
  async fileExists(bucket: string, key: string): Promise<boolean> {
    try {
      this.logger.debug('Checking if file exists in S3', { bucket, key });

      const result = await this.executeWithRetry(async () => {
        const command = new HeadObjectCommand({
          Bucket: bucket,
          Key: key,
        });

        await this.s3Client.send(command);
        return true;
      });

      this.logger.debug('File existence check completed', {
        bucket,
        key,
        exists: result,
      });

      return result;
    } catch (error) {
      // If the error is NotFound, the file doesn't exist
      if (error instanceof NotFound) {
        this.logger.debug('File does not exist in S3', { bucket, key });
        return false;
      }

      this.logger.error('Error checking if file exists in S3', {
        bucket,
        key,
        error: this.formatError(error),
      });

      // Re-throw other errors
      throw new Error(`Error checking if file exists in S3: ${this.formatError(error)}`);
    }
  }

  /**
   * Lists files in a bucket with a prefix
   * @param bucket S3 bucket name
   * @param prefix Prefix to filter objects
   * @returns Promise resolving to array of object keys
   */
  async listFiles(bucket: string, prefix: string): Promise<string[]> {
    try {
      this.logger.debug('Listing files in S3', { bucket, prefix });

      const result = await this.executeWithRetry(async () => {
        const command = new ListObjectsV2Command({
          Bucket: bucket,
          Prefix: prefix,
        });

        const response = await this.s3Client.send(command);
        const keys = response.Contents?.map((item) => item.Key as string) || [];

        return keys;
      });

      this.logger.info('Files listed successfully', {
        bucket,
        prefix,
        count: result.length,
      });

      return result;
    } catch (error) {
      this.logger.error('Failed to list files in S3', {
        bucket,
        prefix,
        error: this.formatError(error),
      });

      throw new Error(`Failed to list files in S3: ${this.formatError(error)}`);
    }
  }

  /**
   * Uploads a document with metadata
   * @param bucket S3 bucket name
   * @param documentData Document content as Buffer
   * @param metadata Document metadata
   * @returns Promise resolving to storage operation result with document key
   */
  async uploadDocument(
    bucket: string,
    documentData: Buffer,
    metadata: IDocumentMetadata
  ): Promise<IStorageResult> {
    // Generate a unique key for the document
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const hash = this.calculateHash(documentData).substring(0, 8);
    const sanitizedFilename = metadata.originalFilename.replace(/[^a-zA-Z0-9._-]/g, '_');
    const key = `documents/${timestamp}_${hash}_${sanitizedFilename}`;

    // Set up storage options with metadata
    const options: IStorageOptions = {
      encryption: 'AES-256',
      contentType: metadata.mimeType || 'application/octet-stream',
      contentDisposition: `attachment; filename="${metadata.originalFilename}"`,
      acl: 'private',
      metadata: {
        'document-type': metadata.documentType || 'unknown',
        'classification-confidence': metadata.classificationConfidence?.toString() || '0',
        'email-id': metadata.emailId,
        'received-at': metadata.receivedAt,
        'processing-status': metadata.processingStatus,
      },
      tags: {
        documentType: metadata.documentType || 'unknown',
        processingStatus: metadata.processingStatus,
        source: 'email-service',
      },
    };

    // Upload the document
    const result = await this.uploadFile(bucket, key, documentData, options);

    // If successful, add the key to the result
    if (result.success) {
      this.logger.info('Document uploaded successfully', {
        bucket,
        key,
        documentType: metadata.documentType,
        size: metadata.size,
        emailId: metadata.emailId,
      });
    }

    return result;
  }

  /**
   * Calculates SHA-256 hash of a buffer
   * @param data Buffer to hash
   * @returns Hex string of the hash
   */
  private calculateHash(data: Buffer): string {
    return createHash('sha256').update(data).digest('hex');
  }

  /**
   * Formats an error for logging
   * @param error Error object
   * @returns Formatted error string
   */
  private formatError(error: unknown): string {
    if (error instanceof S3ServiceException) {
      return `${error.name}: ${error.message} (Code: ${error.$metadata.httpStatusCode})`;
    }
    if (error instanceof Error) {
      return `${error.name}: ${error.message}`;
    }
    return String(error);
  }

  /**
   * Executes a function with retry logic
   * @param fn Function to execute
   * @returns Promise resolving to the function result
   */
  private async executeWithRetry<T>(fn: () => Promise<T>): Promise<T> {
    let lastError: unknown;
    let delay = this.retryConfig.initialDelayMs;

    for (let attempt = 1; attempt <= this.retryConfig.maxRetries + 1; attempt++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error;

        // If this was the last attempt, don't log about retrying
        if (attempt <= this.retryConfig.maxRetries) {
          this.logger.warn(`Operation failed, retrying (${attempt}/${this.retryConfig.maxRetries})`, {
            error: this.formatError(error),
            nextRetryDelayMs: delay,
          });

          // Wait before the next retry
          await new Promise((resolve) => setTimeout(resolve, delay));

          // Increase the delay for the next retry (exponential backoff)
          delay = Math.min(
            delay * this.retryConfig.backoffFactor,
            this.retryConfig.maxDelayMs
          );
        }
      }
    }

    // If we get here, all retries failed
    throw lastError;
  }
}