/**
 * Storage Type Definitions
 * 
 * This module defines TypeScript interfaces for S3-compatible storage operations,
 * bucket configurations, and document metadata used by the Email Service.
 * It provides type definitions for securely storing email attachments in the
 * document repository with AES-256 encryption.
 *
 * The Email Service uses these types to store attachments in S3-compatible storage
 * as specified in the technical requirements. Documents are stored with appropriate
 * metadata and the storage system implements proper error handling and retry logic.
 */

import { IResult, IAsyncResult } from './common';

/**
 * S3 storage configuration
 */
export interface IS3Config {
  /** S3 endpoint URL */
  endpoint: string;
  
  /** S3 region */
  region: string;
  
  /** Default bucket name */
  defaultBucket: string;
  
  /** Access key ID */
  accessKeyId: string;
  
  /** Secret access key */
  secretAccessKey: string;
  
  /** Whether to force path style addressing */
  forcePathStyle?: boolean;
  
  /** Maximum number of concurrent connections */
  maxConnections?: number;
  
  /** Connection timeout in milliseconds */
  connectionTimeout?: number;
  
  /** Whether to use SSL */
  sslEnabled?: boolean;
  
  /** Whether to accelerate endpoint */
  accelerateEndpoint?: boolean;
}

/**
 * Storage options for S3 operations
 */
export interface IStorageOptions {
  /** 
   * Server-side encryption method
   * AES256 is required as per section 0.2.5
   */
  encryption?: 'AES256' | 'aws:kms';
  
  /** KMS key ID if using aws:kms encryption */
  kmsKeyId?: string;
  
  /** Content type of the object */
  contentType?: string;
  
  /** Content disposition */
  contentDisposition?: string;
  
  /** Cache control directives */
  cacheControl?: string;
  
  /** Custom metadata */
  metadata?: Record<string, string>;
  
  /** Object tags */
  tags?: Record<string, string>;
  
  /** Storage class */
  storageClass?: 'STANDARD' | 'REDUCED_REDUNDANCY' | 'STANDARD_IA' | 'ONEZONE_IA' | 'INTELLIGENT_TIERING' | 'GLACIER' | 'DEEP_ARCHIVE';
  
  /** ACL for the object */
  acl?: 'private' | 'public-read' | 'public-read-write' | 'authenticated-read' | 'aws-exec-read' | 'bucket-owner-read' | 'bucket-owner-full-control';
}

/**
 * Document metadata for S3 storage
 */
export interface IDocumentMetadata {
  /** Unique identifier for the document */
  documentId: string;
  
  /** Original filename */
  filename: string;
  
  /** File MIME type */
  mimeType: string;
  
  /** File size in bytes */
  fileSize: number;
  
  /** Document type classification */
  documentType?: string;
  
  /** Classification confidence score (0-1) */
  confidenceScore?: number;
  
  /** Email message ID that contained this document */
  emailMessageId: string;
  
  /** Email sender information */
  sender: {
    /** Sender email address */
    email: string;
    
    /** Sender name if available */
    name?: string;
  };
  
  /** Email subject */
  subject: string;
  
  /** Email received timestamp */
  receivedAt: string;
  
  /** Upload timestamp */
  uploadedAt: string;
  
  /** Processing status */
  status: 'new' | 'processing' | 'processed' | 'failed';
  
  /** Checksum for file integrity verification */
  checksum: string;
  
  /** Checksum algorithm used */
  checksumAlgorithm: 'md5' | 'sha1' | 'sha256';
  
  /** Application ID if this document is associated with an application */
  applicationId?: string;
}

/**
 * Bucket configuration for different environments
 * As specified in section 0.2.5
 */
export interface IBucketConfig {
  /** Bucket name */
  name: string;
  
  /** Whether versioning is enabled */
  versioning: boolean;
  
  /** Default encryption method */
  encryption: 'AES256' | 'aws:kms' | 'none';
  
  /** KMS key ID if using aws:kms encryption */
  kmsKeyId?: string;
  
  /** Lifecycle rules */
  lifecycleRules?: ILifecycleRule[];
  
  /** Bucket policy */
  policy?: Record<string, unknown>;
  
  /** CORS configuration */
  cors?: ICorsRule[];
}

/**
 * Lifecycle rule for S3 buckets
 */
export interface ILifecycleRule {
  /** Rule ID */
  id: string;
  
  /** Whether the rule is enabled */
  enabled: boolean;
  
  /** Prefix filter */
  prefix?: string;
  
  /** Tag filters */
  tags?: Record<string, string>;
  
  /** Expiration configuration */
  expiration?: {
    /** Days after which objects expire */
    days?: number;
    
    /** Date after which objects expire */
    date?: string;
  };
  
  /** Transition configuration */
  transitions?: Array<{
    /** Days after which objects transition */
    days: number;
    
    /** Storage class to transition to */
    storageClass: string;
  }>;
}

/**
 * CORS rule for S3 buckets
 */
export interface ICorsRule {
  /** Allowed origins */
  allowedOrigins: string[];
  
  /** Allowed methods */
  allowedMethods: Array<'GET' | 'PUT' | 'POST' | 'DELETE' | 'HEAD'>;
  
  /** Allowed headers */
  allowedHeaders: string[];
  
  /** Exposed headers */
  exposedHeaders?: string[];
  
  /** Max age in seconds */
  maxAgeSeconds?: number;
}

/**
 * Signed URL options
 */
export interface ISignedUrlOptions {
  /** URL expiration time in seconds */
  expiresIn: number;
  
  /** HTTP method */
  method: 'GET' | 'PUT' | 'POST' | 'DELETE';
  
  /** Content type (for PUT/POST) */
  contentType?: string;
  
  /** Additional query parameters */
  queryParams?: Record<string, string>;
}

/**
 * Storage operation result
 */
export interface IStorageOperationResult {
  /** Success status */
  success: boolean;
  
  /** S3 key of the stored object */
  key?: string;
  
  /** S3 bucket where the object is stored */
  bucket?: string;
  
  /** ETag of the stored object */
  etag?: string;
  
  /** Version ID if versioning is enabled */
  versionId?: string;
  
  /** Error message if operation failed */
  error?: string;
  
  /** Detailed error information */
  errorDetails?: Record<string, unknown>;
}

/**
 * Storage service interface
 */
export interface IStorageService {
  /**
   * Upload a file to S3 storage
   * 
   * @param filePath - Local file path to upload
   * @param key - S3 object key
   * @param metadata - Document metadata
   * @param options - Storage options
   * @param bucket - Optional bucket name (uses default if not specified)
   */
  uploadFile(
    filePath: string,
    key: string,
    metadata: IDocumentMetadata,
    options?: IStorageOptions,
    bucket?: string
  ): IAsyncResult<IStorageOperationResult>;
  
  /**
   * Upload a buffer to S3 storage
   * 
   * @param buffer - Buffer to upload
   * @param key - S3 object key
   * @param metadata - Document metadata
   * @param options - Storage options
   * @param bucket - Optional bucket name (uses default if not specified)
   */
  uploadBuffer(
    buffer: Buffer,
    key: string,
    metadata: IDocumentMetadata,
    options?: IStorageOptions,
    bucket?: string
  ): IAsyncResult<IStorageOperationResult>;
  
  /**
   * Download a file from S3 storage
   * 
   * @param key - S3 object key
   * @param destinationPath - Local destination path
   * @param bucket - Optional bucket name (uses default if not specified)
   */
  downloadFile(
    key: string,
    destinationPath: string,
    bucket?: string
  ): IAsyncResult<IStorageOperationResult>;
  
  /**
   * Download a file as a buffer from S3 storage
   * 
   * @param key - S3 object key
   * @param bucket - Optional bucket name (uses default if not specified)
   */
  downloadBuffer(
    key: string,
    bucket?: string
  ): IAsyncResult<Buffer>;
  
  /**
   * Delete a file from S3 storage
   * 
   * @param key - S3 object key
   * @param bucket - Optional bucket name (uses default if not specified)
   */
  deleteFile(
    key: string,
    bucket?: string
  ): IAsyncResult<IStorageOperationResult>;
  
  /**
   * Check if a file exists in S3 storage
   * 
   * @param key - S3 object key
   * @param bucket - Optional bucket name (uses default if not specified)
   */
  fileExists(
    key: string,
    bucket?: string
  ): IAsyncResult<boolean>;
  
  /**
   * Get metadata for a file in S3 storage
   * 
   * @param key - S3 object key
   * @param bucket - Optional bucket name (uses default if not specified)
   */
  getMetadata(
    key: string,
    bucket?: string
  ): IAsyncResult<IDocumentMetadata>;
  
  /**
   * Update metadata for a file in S3 storage
   * 
   * @param key - S3 object key
   * @param metadata - Document metadata
   * @param bucket - Optional bucket name (uses default if not specified)
   */
  updateMetadata(
    key: string,
    metadata: Partial<IDocumentMetadata>,
    bucket?: string
  ): IAsyncResult<IStorageOperationResult>;
  
  /**
   * Generate a signed URL for a file in S3 storage
   * 
   * @param key - S3 object key
   * @param options - Signed URL options
   * @param bucket - Optional bucket name (uses default if not specified)
   */
  getSignedUrl(
    key: string,
    options: ISignedUrlOptions,
    bucket?: string
  ): IAsyncResult<string>;
}

/**
 * Default bucket configurations for different environments
 * As specified in section 0.2.5
 */
export const DEFAULT_BUCKET_CONFIGS: Record<string, IBucketConfig> = {
  production: {
    name: 'mca-documents-production',
    versioning: true,
    encryption: 'AES256',
    lifecycleRules: [
      {
        id: 'archive-rule',
        enabled: true,
        transitions: [
          {
            days: 90,
            storageClass: 'STANDARD_IA'
          },
          {
            days: 365,
            storageClass: 'GLACIER'
          }
        ]
      }
    ]
  },
  staging: {
    name: 'mca-documents-staging',
    versioning: true,
    encryption: 'AES256',
    lifecycleRules: [
      {
        id: 'archive-rule',
        enabled: true,
        transitions: [
          {
            days: 30,
            storageClass: 'STANDARD_IA'
          }
        ]
      }
    ]
  },
  development: {
    name: 'mca-documents-development',
    versioning: true,
    encryption: 'AES256',
    lifecycleRules: []
  }
};

/**
 * Default storage options with AES-256 encryption
 * As required in section 0.2.5
 */
export const DEFAULT_STORAGE_OPTIONS: IStorageOptions = {
  encryption: 'AES256',
  acl: 'private',
  storageClass: 'STANDARD',
  cacheControl: 'private, max-age=0, no-cache, no-store'
};

/**
 * Default signed URL expiration time (15 minutes)
 */
export const DEFAULT_SIGNED_URL_EXPIRATION = 15 * 60; // 15 minutes in seconds