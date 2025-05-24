/**
 * Storage Service for Email Service
 * 
 * This service provides functionality for storing email attachments in S3-compatible storage
 * with AES-256 encryption. It ensures that documents are securely stored and accessible
 * for processing by other services in the MCA Application Processing System.
 * 
 * Key features:
 * - S3 client connection with AES-256 encryption
 * - Document storage with appropriate metadata
 * - Error handling with retry logic for storage operations
 * - Environment-specific storage configuration
 * - Secure access to stored documents
 */

import fs from 'fs';
import path from 'path';
import { createHash } from 'crypto';
import { promisify } from 'util';

import {
  S3Client,
  PutObjectCommand,
  GetObjectCommand,
  DeleteObjectCommand,
  HeadObjectCommand,
  CopyObjectCommand,
  S3ServiceException,
  NotFound
} from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

import logger, { createComponentLogger, logError } from '../config/logger';
import s3Config, { s3Client, getCurrentBucket, handleS3Error, generateAttachmentKey } from '../config/s3';
import { withRetry, S3_RETRY_OPTIONS, RetryOptions } from '../utils/retry';
import {
  IStorageService,
  IDocumentMetadata,
  IStorageOptions,
  IStorageOperationResult,
  ISignedUrlOptions,
  DEFAULT_STORAGE_OPTIONS
} from '../types/storage';
import { IResult, IAsyncResult } from '../types/common';

// Create a component-specific logger
const storageLogger = createComponentLogger('StorageService');

// Promisify fs functions
const readFile = promisify(fs.readFile);
const writeFile = promisify(fs.writeFile);
const mkdir = promisify(fs.mkdir);

/**
 * Implementation of the Storage Service
 * 
 * This class provides methods for storing, retrieving, and managing email attachments
 * in S3-compatible storage with AES-256 encryption.
 */
export class StorageService implements IStorageService {
  private s3Client: S3Client;
  private retryOptions: RetryOptions;

  /**
   * Creates a new instance of the StorageService
   * 
   * @param client - Optional S3 client (uses default if not provided)
   * @param options - Optional retry options (uses S3_RETRY_OPTIONS if not provided)
   */
  constructor(client?: S3Client, options?: RetryOptions) {
    this.s3Client = client || s3Client;
    this.retryOptions = options || S3_RETRY_OPTIONS;
    
    storageLogger.info('Storage service initialized', {
      endpoint: s3Config.endpoint,
      region: s3Config.region,
      defaultBucket: getCurrentBucket().name
    });
  }

  /**
   * Uploads a file to S3 storage with AES-256 encryption
   * 
   * @param filePath - Local file path to upload
   * @param key - S3 object key (if not provided, generates one based on the file path)
   * @param metadata - Document metadata
   * @param options - Storage options (uses DEFAULT_STORAGE_OPTIONS if not provided)
   * @param bucket - Optional bucket name (uses default if not specified)
   * @returns A promise that resolves with the storage operation result
   */
  async uploadFile(
    filePath: string,
    key: string,
    metadata: IDocumentMetadata,
    options?: IStorageOptions,
    bucket?: string
  ): IAsyncResult<IStorageOperationResult> {
    try {
      // Generate a key if not provided
      const objectKey = key || generateAttachmentKey(metadata.emailMessageId, path.basename(filePath));
      
      // Read the file
      const fileContent = await readFile(filePath);
      
      // Calculate checksum for integrity verification
      const checksum = createHash('md5').update(fileContent).digest('hex');
      
      // Update metadata with checksum
      const updatedMetadata = {
        ...metadata,
        checksum,
        checksumAlgorithm: 'md5' as const
      };
      
      // Upload the file
      return this.uploadBuffer(fileContent, objectKey, updatedMetadata, options, bucket);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      logError(storageLogger, `Failed to upload file ${filePath}`, error instanceof Error ? error : new Error(errorMessage), {
        filePath,
        key,
        documentId: metadata.documentId,
        emailMessageId: metadata.emailMessageId
      });
      
      return {
        success: false,
        error: {
          code: 'UPLOAD_FAILED',
          message: `Failed to upload file: ${errorMessage}`,
          timestamp: Date.now()
        }
      };
    }
  }

  /**
   * Uploads a buffer to S3 storage with AES-256 encryption
   * 
   * @param buffer - Buffer to upload
   * @param key - S3 object key
   * @param metadata - Document metadata
   * @param options - Storage options (uses DEFAULT_STORAGE_OPTIONS if not provided)
   * @param bucket - Optional bucket name (uses default if not specified)
   * @returns A promise that resolves with the storage operation result
   */
  async uploadBuffer(
    buffer: Buffer,
    key: string,
    metadata: IDocumentMetadata,
    options?: IStorageOptions,
    bucket?: string
  ): IAsyncResult<IStorageOperationResult> {
    const bucketName = bucket || getCurrentBucket().name;
    const storageOptions = { ...DEFAULT_STORAGE_OPTIONS, ...options };
    
    // Convert metadata to string values for S3 metadata
    const s3Metadata: Record<string, string> = {};
    Object.entries(metadata).forEach(([k, v]) => {
      if (v !== undefined && v !== null) {
        if (typeof v === 'object') {
          s3Metadata[k] = JSON.stringify(v);
        } else {
          s3Metadata[k] = String(v);
        }
      }
    });
    
    // Create the PutObjectCommand
    const command = new PutObjectCommand({
      Bucket: bucketName,
      Key: key,
      Body: buffer,
      ContentType: storageOptions.contentType || metadata.mimeType,
      ContentDisposition: storageOptions.contentDisposition,
      CacheControl: storageOptions.cacheControl,
      Metadata: { ...s3Metadata, ...storageOptions.metadata },
      ServerSideEncryption: storageOptions.encryption || 'AES256', // Ensure AES-256 encryption
      StorageClass: storageOptions.storageClass,
      ACL: storageOptions.acl || 'private',
      Tagging: storageOptions.tags ? this.formatTags(storageOptions.tags) : undefined
    });
    
    try {
      // Use retry logic for the upload operation
      const result = await withRetry(
        async () => {
          storageLogger.debug(`Uploading object to S3: ${key}`, { bucket: bucketName, size: buffer.length });
          return this.s3Client.send(command);
        },
        this.retryOptions
      );
      
      if (!result.success) {
        throw result.error;
      }
      
      storageLogger.info(`Successfully uploaded object to S3: ${key}`, {
        bucket: bucketName,
        documentId: metadata.documentId,
        emailMessageId: metadata.emailMessageId,
        etag: result.result?.ETag,
        size: buffer.length
      });
      
      return {
        success: true,
        data: {
          success: true,
          key,
          bucket: bucketName,
          etag: result.result?.ETag?.replace(/"/g, ''), // Remove quotes from ETag
          versionId: result.result?.VersionId
        }
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      logError(storageLogger, `Failed to upload buffer to S3: ${key}`, error instanceof Error ? error : new Error(errorMessage), {
        bucket: bucketName,
        key,
        documentId: metadata.documentId,
        emailMessageId: metadata.emailMessageId,
        size: buffer.length
      });
      
      return {
        success: false,
        error: {
          code: 'UPLOAD_FAILED',
          message: `Failed to upload buffer: ${errorMessage}`,
          timestamp: Date.now(),
          context: {
            bucket: bucketName,
            key,
            documentId: metadata.documentId
          }
        }
      };
    }
  }

  /**
   * Downloads a file from S3 storage
   * 
   * @param key - S3 object key
   * @param destinationPath - Local destination path
   * @param bucket - Optional bucket name (uses default if not specified)
   * @returns A promise that resolves with the storage operation result
   */
  async downloadFile(
    key: string,
    destinationPath: string,
    bucket?: string
  ): IAsyncResult<IStorageOperationResult> {
    try {
      // Download the file as a buffer
      const bufferResult = await this.downloadBuffer(key, bucket);
      
      if (!bufferResult.success) {
        return {
          success: false,
          error: bufferResult.error
        };
      }
      
      // Ensure the directory exists
      const dir = path.dirname(destinationPath);
      await mkdir(dir, { recursive: true });
      
      // Write the buffer to the destination path
      await writeFile(destinationPath, bufferResult.data);
      
      storageLogger.info(`Successfully downloaded object from S3: ${key}`, {
        bucket: bucket || getCurrentBucket().name,
        destinationPath,
        size: bufferResult.data.length
      });
      
      return {
        success: true,
        data: {
          success: true,
          key,
          bucket: bucket || getCurrentBucket().name
        }
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      logError(storageLogger, `Failed to download file from S3: ${key}`, error instanceof Error ? error : new Error(errorMessage), {
        bucket: bucket || getCurrentBucket().name,
        key,
        destinationPath
      });
      
      return {
        success: false,
        error: {
          code: 'DOWNLOAD_FAILED',
          message: `Failed to download file: ${errorMessage}`,
          timestamp: Date.now(),
          context: {
            bucket: bucket || getCurrentBucket().name,
            key,
            destinationPath
          }
        }
      };
    }
  }

  /**
   * Downloads a file as a buffer from S3 storage
   * 
   * @param key - S3 object key
   * @param bucket - Optional bucket name (uses default if not specified)
   * @returns A promise that resolves with the file buffer
   */
  async downloadBuffer(
    key: string,
    bucket?: string
  ): IAsyncResult<Buffer> {
    const bucketName = bucket || getCurrentBucket().name;
    
    // Create the GetObjectCommand
    const command = new GetObjectCommand({
      Bucket: bucketName,
      Key: key
    });
    
    try {
      // Use retry logic for the download operation
      const result = await withRetry(
        async () => {
          storageLogger.debug(`Downloading object from S3: ${key}`, { bucket: bucketName });
          return this.s3Client.send(command);
        },
        this.retryOptions
      );
      
      if (!result.success) {
        throw result.error;
      }
      
      // Get the response body as a buffer
      const response = result.result;
      if (!response.Body) {
        throw new Error('Response body is empty');
      }
      
      // Convert the readable stream to a buffer
      const chunks: Uint8Array[] = [];
      for await (const chunk of response.Body as any) {
        chunks.push(chunk);
      }
      
      const buffer = Buffer.concat(chunks);
      
      storageLogger.debug(`Successfully downloaded object from S3: ${key}`, {
        bucket: bucketName,
        size: buffer.length
      });
      
      return {
        success: true,
        data: buffer
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      
      // Handle not found errors specifically
      if (error instanceof NotFound || (error instanceof S3ServiceException && error.name === 'NoSuchKey')) {
        storageLogger.warn(`Object not found in S3: ${key}`, {
          bucket: bucketName,
          key
        });
        
        return {
          success: false,
          error: {
            code: 'OBJECT_NOT_FOUND',
            message: `Object not found: ${key}`,
            timestamp: Date.now(),
            context: {
              bucket: bucketName,
              key
            }
          }
        };
      }
      
      logError(storageLogger, `Failed to download buffer from S3: ${key}`, error instanceof Error ? error : new Error(errorMessage), {
        bucket: bucketName,
        key
      });
      
      return {
        success: false,
        error: {
          code: 'DOWNLOAD_FAILED',
          message: `Failed to download buffer: ${errorMessage}`,
          timestamp: Date.now(),
          context: {
            bucket: bucketName,
            key
          }
        }
      };
    }
  }

  /**
   * Deletes a file from S3 storage
   * 
   * @param key - S3 object key
   * @param bucket - Optional bucket name (uses default if not specified)
   * @returns A promise that resolves with the storage operation result
   */
  async deleteFile(
    key: string,
    bucket?: string
  ): IAsyncResult<IStorageOperationResult> {
    const bucketName = bucket || getCurrentBucket().name;
    
    // Create the DeleteObjectCommand
    const command = new DeleteObjectCommand({
      Bucket: bucketName,
      Key: key
    });
    
    try {
      // Use retry logic for the delete operation
      const result = await withRetry(
        async () => {
          storageLogger.debug(`Deleting object from S3: ${key}`, { bucket: bucketName });
          return this.s3Client.send(command);
        },
        this.retryOptions
      );
      
      if (!result.success) {
        throw result.error;
      }
      
      storageLogger.info(`Successfully deleted object from S3: ${key}`, {
        bucket: bucketName,
        versionId: result.result?.VersionId
      });
      
      return {
        success: true,
        data: {
          success: true,
          key,
          bucket: bucketName,
          versionId: result.result?.VersionId
        }
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      
      // Handle not found errors specifically (not an error if the file doesn't exist)
      if (error instanceof NotFound || (error instanceof S3ServiceException && error.name === 'NoSuchKey')) {
        storageLogger.warn(`Object not found for deletion in S3: ${key}`, {
          bucket: bucketName,
          key
        });
        
        // Return success for idempotency
        return {
          success: true,
          data: {
            success: true,
            key,
            bucket: bucketName
          }
        };
      }
      
      logError(storageLogger, `Failed to delete file from S3: ${key}`, error instanceof Error ? error : new Error(errorMessage), {
        bucket: bucketName,
        key
      });
      
      return {
        success: false,
        error: {
          code: 'DELETE_FAILED',
          message: `Failed to delete file: ${errorMessage}`,
          timestamp: Date.now(),
          context: {
            bucket: bucketName,
            key
          }
        }
      };
    }
  }

  /**
   * Checks if a file exists in S3 storage
   * 
   * @param key - S3 object key
   * @param bucket - Optional bucket name (uses default if not specified)
   * @returns A promise that resolves with a boolean indicating if the file exists
   */
  async fileExists(
    key: string,
    bucket?: string
  ): IAsyncResult<boolean> {
    const bucketName = bucket || getCurrentBucket().name;
    
    // Create the HeadObjectCommand
    const command = new HeadObjectCommand({
      Bucket: bucketName,
      Key: key
    });
    
    try {
      // Use retry logic for the head operation
      const result = await withRetry(
        async () => {
          storageLogger.debug(`Checking if object exists in S3: ${key}`, { bucket: bucketName });
          return this.s3Client.send(command);
        },
        this.retryOptions
      );
      
      if (!result.success) {
        throw result.error;
      }
      
      storageLogger.debug(`Object exists in S3: ${key}`, {
        bucket: bucketName,
        etag: result.result?.ETag,
        lastModified: result.result?.LastModified
      });
      
      return {
        success: true,
        data: true
      };
    } catch (error) {
      // Handle not found errors specifically
      if (error instanceof NotFound || (error instanceof S3ServiceException && error.name === 'NotFound')) {
        storageLogger.debug(`Object does not exist in S3: ${key}`, {
          bucket: bucketName,
          key
        });
        
        return {
          success: true,
          data: false
        };
      }
      
      const errorMessage = error instanceof Error ? error.message : String(error);
      logError(storageLogger, `Failed to check if file exists in S3: ${key}`, error instanceof Error ? error : new Error(errorMessage), {
        bucket: bucketName,
        key
      });
      
      return {
        success: false,
        error: {
          code: 'HEAD_FAILED',
          message: `Failed to check if file exists: ${errorMessage}`,
          timestamp: Date.now(),
          context: {
            bucket: bucketName,
            key
          }
        }
      };
    }
  }

  /**
   * Gets metadata for a file in S3 storage
   * 
   * @param key - S3 object key
   * @param bucket - Optional bucket name (uses default if not specified)
   * @returns A promise that resolves with the document metadata
   */
  async getMetadata(
    key: string,
    bucket?: string
  ): IAsyncResult<IDocumentMetadata> {
    const bucketName = bucket || getCurrentBucket().name;
    
    // Create the HeadObjectCommand
    const command = new HeadObjectCommand({
      Bucket: bucketName,
      Key: key
    });
    
    try {
      // Use retry logic for the head operation
      const result = await withRetry(
        async () => {
          storageLogger.debug(`Getting metadata for object in S3: ${key}`, { bucket: bucketName });
          return this.s3Client.send(command);
        },
        this.retryOptions
      );
      
      if (!result.success) {
        throw result.error;
      }
      
      const response = result.result;
      const metadata = response.Metadata || {};
      
      // Parse metadata values
      const parsedMetadata: Record<string, any> = {};
      Object.entries(metadata).forEach(([k, v]) => {
        if (v) {
          try {
            // Try to parse JSON values
            parsedMetadata[k] = JSON.parse(v);
          } catch {
            // If not JSON, use the string value
            parsedMetadata[k] = v;
          }
        }
      });
      
      // Construct document metadata from S3 metadata
      // Use default values for required fields if not present
      const documentMetadata: IDocumentMetadata = {
        documentId: parsedMetadata.documentId || key,
        filename: parsedMetadata.filename || path.basename(key),
        mimeType: parsedMetadata.mimeType || response.ContentType || 'application/octet-stream',
        fileSize: parsedMetadata.fileSize || response.ContentLength || 0,
        documentType: parsedMetadata.documentType,
        confidenceScore: parsedMetadata.confidenceScore !== undefined ? Number(parsedMetadata.confidenceScore) : undefined,
        emailMessageId: parsedMetadata.emailMessageId || '',
        sender: parsedMetadata.sender || { email: '' },
        subject: parsedMetadata.subject || '',
        receivedAt: parsedMetadata.receivedAt || '',
        uploadedAt: parsedMetadata.uploadedAt || new Date(response.LastModified || Date.now()).toISOString(),
        status: parsedMetadata.status || 'new',
        checksum: parsedMetadata.checksum || '',
        checksumAlgorithm: parsedMetadata.checksumAlgorithm || 'md5',
        applicationId: parsedMetadata.applicationId
      };
      
      storageLogger.debug(`Successfully retrieved metadata for object in S3: ${key}`, {
        bucket: bucketName,
        documentId: documentMetadata.documentId
      });
      
      return {
        success: true,
        data: documentMetadata
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      
      // Handle not found errors specifically
      if (error instanceof NotFound || (error instanceof S3ServiceException && error.name === 'NotFound')) {
        storageLogger.warn(`Object not found when getting metadata in S3: ${key}`, {
          bucket: bucketName,
          key
        });
        
        return {
          success: false,
          error: {
            code: 'OBJECT_NOT_FOUND',
            message: `Object not found: ${key}`,
            timestamp: Date.now(),
            context: {
              bucket: bucketName,
              key
            }
          }
        };
      }
      
      logError(storageLogger, `Failed to get metadata for file in S3: ${key}`, error instanceof Error ? error : new Error(errorMessage), {
        bucket: bucketName,
        key
      });
      
      return {
        success: false,
        error: {
          code: 'GET_METADATA_FAILED',
          message: `Failed to get metadata: ${errorMessage}`,
          timestamp: Date.now(),
          context: {
            bucket: bucketName,
            key
          }
        }
      };
    }
  }

  /**
   * Updates metadata for a file in S3 storage
   * 
   * @param key - S3 object key
   * @param metadata - Document metadata to update
   * @param bucket - Optional bucket name (uses default if not specified)
   * @returns A promise that resolves with the storage operation result
   */
  async updateMetadata(
    key: string,
    metadata: Partial<IDocumentMetadata>,
    bucket?: string
  ): IAsyncResult<IStorageOperationResult> {
    const bucketName = bucket || getCurrentBucket().name;
    
    try {
      // First, get the existing metadata
      const existingMetadataResult = await this.getMetadata(key, bucketName);
      
      if (!existingMetadataResult.success) {
        return {
          success: false,
          error: existingMetadataResult.error
        };
      }
      
      // Merge the existing metadata with the new metadata
      const mergedMetadata = {
        ...existingMetadataResult.data,
        ...metadata
      };
      
      // Create the CopyObjectCommand to update metadata
      // S3 doesn't allow direct metadata updates, so we need to copy the object to itself
      const command = new CopyObjectCommand({
        Bucket: bucketName,
        Key: key,
        CopySource: `${bucketName}/${encodeURIComponent(key)}`,
        Metadata: this.convertMetadataToS3Format(mergedMetadata),
        MetadataDirective: 'REPLACE',
        ServerSideEncryption: 'AES256', // Ensure AES-256 encryption is maintained
        ACL: 'private'
      });
      
      // Use retry logic for the copy operation
      const result = await withRetry(
        async () => {
          storageLogger.debug(`Updating metadata for object in S3: ${key}`, { bucket: bucketName });
          return this.s3Client.send(command);
        },
        this.retryOptions
      );
      
      if (!result.success) {
        throw result.error;
      }
      
      storageLogger.info(`Successfully updated metadata for object in S3: ${key}`, {
        bucket: bucketName,
        documentId: mergedMetadata.documentId,
        etag: result.result?.CopyObjectResult?.ETag,
        versionId: result.result?.VersionId
      });
      
      return {
        success: true,
        data: {
          success: true,
          key,
          bucket: bucketName,
          etag: result.result?.CopyObjectResult?.ETag?.replace(/"/g, ''), // Remove quotes from ETag
          versionId: result.result?.VersionId
        }
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      logError(storageLogger, `Failed to update metadata for file in S3: ${key}`, error instanceof Error ? error : new Error(errorMessage), {
        bucket: bucketName,
        key,
        metadata: JSON.stringify(metadata)
      });
      
      return {
        success: false,
        error: {
          code: 'UPDATE_METADATA_FAILED',
          message: `Failed to update metadata: ${errorMessage}`,
          timestamp: Date.now(),
          context: {
            bucket: bucketName,
            key
          }
        }
      };
    }
  }

  /**
   * Generates a signed URL for a file in S3 storage
   * 
   * @param key - S3 object key
   * @param options - Signed URL options
   * @param bucket - Optional bucket name (uses default if not specified)
   * @returns A promise that resolves with the signed URL
   */
  async getSignedUrl(
    key: string,
    options: ISignedUrlOptions,
    bucket?: string
  ): IAsyncResult<string> {
    const bucketName = bucket || getCurrentBucket().name;
    
    try {
      // Create the appropriate command based on the HTTP method
      let command;
      switch (options.method) {
        case 'GET':
          command = new GetObjectCommand({
            Bucket: bucketName,
            Key: key
          });
          break;
        case 'PUT':
          command = new PutObjectCommand({
            Bucket: bucketName,
            Key: key,
            ContentType: options.contentType,
            ServerSideEncryption: 'AES256', // Ensure AES-256 encryption
            ACL: 'private'
          });
          break;
        default:
          throw new Error(`Unsupported method: ${options.method}`);
      }
      
      // Generate the signed URL
      const signedUrl = await getSignedUrl(this.s3Client, command, {
        expiresIn: options.expiresIn
      });
      
      storageLogger.debug(`Generated signed URL for object in S3: ${key}`, {
        bucket: bucketName,
        method: options.method,
        expiresIn: options.expiresIn
      });
      
      return {
        success: true,
        data: signedUrl
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      logError(storageLogger, `Failed to generate signed URL for file in S3: ${key}`, error instanceof Error ? error : new Error(errorMessage), {
        bucket: bucketName,
        key,
        method: options.method
      });
      
      return {
        success: false,
        error: {
          code: 'SIGNED_URL_FAILED',
          message: `Failed to generate signed URL: ${errorMessage}`,
          timestamp: Date.now(),
          context: {
            bucket: bucketName,
            key,
            method: options.method
          }
        }
      };
    }
  }

  /**
   * Formats tags for S3 tagging
   * 
   * @param tags - Tags object
   * @returns Formatted tags string
   */
  private formatTags(tags: Record<string, string>): string {
    return Object.entries(tags)
      .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
      .join('&');
  }

  /**
   * Converts document metadata to S3 metadata format
   * 
   * @param metadata - Document metadata
   * @returns S3 metadata format
   */
  private convertMetadataToS3Format(metadata: Partial<IDocumentMetadata>): Record<string, string> {
    const s3Metadata: Record<string, string> = {};
    
    Object.entries(metadata).forEach(([k, v]) => {
      if (v !== undefined && v !== null) {
        if (typeof v === 'object') {
          s3Metadata[k] = JSON.stringify(v);
        } else {
          s3Metadata[k] = String(v);
        }
      }
    });
    
    return s3Metadata;
  }
}

/**
 * Singleton instance of the StorageService
 */
export const storageService = new StorageService();

/**
 * Default export for the StorageService
 */
export default storageService;