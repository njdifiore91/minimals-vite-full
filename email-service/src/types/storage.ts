/**
 * @file storage.ts
 * @description TypeScript interfaces for S3-compatible storage operations, bucket configurations, 
 * and document metadata used by the Email Service. This file provides type definitions for securely 
 * storing email attachments in the document repository.
 */

import { IResult } from './common';

// ----------------------------------------------------------------------

/**
 * S3 credentials configuration
 */
export interface IS3Credentials {
  /** AWS access key ID */
  accessKeyId: string;
  /** AWS secret access key */
  secretAccessKey: string;
  /** Optional session token for temporary credentials */
  sessionToken?: string;
}

/**
 * S3 configuration interface for connection parameters
 */
export interface IS3Config {
  /** S3 endpoint URL */
  endpoint: string;
  /** S3 region */
  region: string;
  /** S3 credentials */
  credentials: IS3Credentials;
  /** Whether to force path style URLs */
  forcePathStyle?: boolean;
  /** Maximum number of retries for S3 operations */
  maxRetries?: number;
  /** Connection timeout in milliseconds */
  connectionTimeout?: number;
  /** Socket timeout in milliseconds */
  socketTimeout?: number;
}

/**
 * Storage options for configuring encryption and access controls
 */
export interface IStorageOptions {
  /** Encryption algorithm (AES-256 required) */
  encryption: 'AES-256';
  /** Content type of the stored object */
  contentType?: string;
  /** Cache control header */
  cacheControl?: string;
  /** Content disposition header */
  contentDisposition?: string;
  /** Metadata to be stored with the object */
  metadata?: Record<string, string>;
  /** Tags to be applied to the object */
  tags?: Record<string, string>;
  /** ACL for the object */
  acl?: 'private' | 'public-read' | 'authenticated-read';
}

/**
 * Document metadata for storing classification and processing information
 */
export interface IDocumentMetadata {
  /** Original filename */
  originalFilename: string;
  /** Document type classification */
  documentType?: string;
  /** Classification confidence score (0-1) */
  classificationConfidence?: number;
  /** Email ID this document was attached to */
  emailId: string;
  /** Timestamp when the document was received */
  receivedAt: string;
  /** Timestamp when the document was stored */
  storedAt: string;
  /** Processing status */
  processingStatus: 'pending' | 'processing' | 'processed' | 'failed';
  /** Error message if processing failed */
  processingError?: string;
  /** Document size in bytes */
  size: number;
  /** Document MIME type */
  mimeType: string;
  /** Document hash (SHA-256) */
  hash?: string;
  /** Additional metadata fields */
  additionalMetadata?: Record<string, unknown>;
}

/**
 * Bucket configuration for different environments
 */
export interface IBucketConfig {
  /** Bucket name */
  name: string;
  /** Bucket region */
  region: string;
  /** Whether versioning is enabled */
  versioning: boolean;
  /** Lifecycle rules */
  lifecycleRules?: {
    /** Rule ID */
    id: string;
    /** Rule prefix */
    prefix: string;
    /** Expiration in days */
    expirationDays?: number;
    /** Transition to storage class after days */
    transitionDays?: number;
    /** Storage class to transition to */
    storageClass?: string;
  }[];
}

/**
 * Environment-specific bucket configurations
 */
export interface IBucketEnvironmentConfig {
  /** Production bucket configuration */
  production: IBucketConfig;
  /** Staging bucket configuration */
  staging: IBucketConfig;
  /** Development bucket configuration */
  development: IBucketConfig;
}

/**
 * Storage operation result for error handling and status tracking
 */
export interface IStorageResult extends IResult {
  /** S3 object key */
  key?: string;
  /** S3 object URL */
  url?: string;
  /** S3 object ETag */
  etag?: string;
  /** S3 object version ID (if versioning is enabled) */
  versionId?: string;
}

/**
 * Signed URL options
 */
export interface ISignedUrlOptions {
  /** URL expiration time in seconds */
  expiresIn: number;
  /** HTTP method for the signed URL */
  method?: 'GET' | 'PUT';
  /** Content type for PUT requests */
  contentType?: string;
  /** Response content type for GET requests */
  responseContentType?: string;
  /** Response content disposition for GET requests */
  responseContentDisposition?: string;
}

/**
 * Storage service interface
 */
export interface IStorageService {
  /** Upload a file to S3 */
  uploadFile(bucket: string, key: string, body: Buffer, options?: IStorageOptions): Promise<IStorageResult>;
  /** Download a file from S3 */
  downloadFile(bucket: string, key: string): Promise<Buffer>;
  /** Generate a signed URL for temporary access */
  getSignedUrl(bucket: string, key: string, options: ISignedUrlOptions): Promise<string>;
  /** Delete a file from S3 */
  deleteFile(bucket: string, key: string): Promise<IStorageResult>;
  /** Check if a file exists in S3 */
  fileExists(bucket: string, key: string): Promise<boolean>;
  /** List files in a bucket with a prefix */
  listFiles(bucket: string, prefix: string): Promise<string[]>;
}