/**
 * S3 Storage Configuration
 * 
 * This module configures the S3-compatible storage client for the Email Service
 * to securely store email attachments. It defines connection parameters, bucket settings,
 * encryption options, and access controls according to the technical requirements.
 * 
 * Key features:
 * - AES-256 encryption for all stored objects
 * - Environment-specific bucket configuration
 * - Secure credential management
 * - Connection options with appropriate timeouts
 * - Error handling and retry logic
 */

import { S3Client, S3ClientConfig, ServerSideEncryption } from '@aws-sdk/client-s3';
import { NodeHttpHandler } from '@aws-sdk/node-http-handler';
import { DEFAULT_RETRY_MODE } from '@aws-sdk/middleware-retry';

import { IS3Config, DEFAULT_BUCKET_CONFIGS, IBucketConfig } from '../types/storage';
import { IRetryConfig } from '../types/common';
import appConfig from './app';

/**
 * Default retry configuration for S3 operations
 */
const DEFAULT_S3_RETRY_CONFIG: IRetryConfig = {
  maxAttempts: 3,
  baseDelayMs: 100,
  useExponentialBackoff: true,
  maxDelayMs: 5000
};

/**
 * Environment-specific S3 configuration
 */
const s3Config: IS3Config = {
  // S3 endpoint URL - use environment variable or default to AWS S3
  endpoint: process.env.S3_ENDPOINT || 'https://s3.amazonaws.com',
  
  // S3 region - use environment variable or default to us-east-1
  region: process.env.S3_REGION || 'us-east-1',
  
  // Default bucket based on environment
  defaultBucket: DEFAULT_BUCKET_CONFIGS[appConfig.env]?.name || 'mca-documents-development',
  
  // Access credentials from environment variables
  accessKeyId: process.env.S3_ACCESS_KEY_ID || '',
  secretAccessKey: process.env.S3_SECRET_ACCESS_KEY || '',
  
  // Use path style addressing for compatibility with S3-compatible storage
  forcePathStyle: process.env.S3_FORCE_PATH_STYLE === 'true',
  
  // Connection settings
  maxConnections: parseInt(process.env.S3_MAX_CONNECTIONS || '10', 10),
  connectionTimeout: parseInt(process.env.S3_CONNECTION_TIMEOUT || '5000', 10),
  
  // Security settings
  sslEnabled: process.env.S3_SSL_ENABLED !== 'false', // Default to true
  
  // Performance settings
  accelerateEndpoint: process.env.S3_ACCELERATE_ENDPOINT === 'true'
};

/**
 * Validate S3 configuration
 */
const validateS3Config = (config: IS3Config): void => {
  if (!config.accessKeyId) {
    throw new Error('S3_ACCESS_KEY_ID environment variable is required');
  }
  
  if (!config.secretAccessKey) {
    throw new Error('S3_SECRET_ACCESS_KEY environment variable is required');
  }
  
  if (!config.defaultBucket) {
    throw new Error('Default S3 bucket name is required');
  }
  
  // Validate bucket configuration exists for the current environment
  if (!DEFAULT_BUCKET_CONFIGS[appConfig.env]) {
    throw new Error(`No bucket configuration found for environment: ${appConfig.env}`);
  }
  
  // Validate connection settings
  if (config.maxConnections <= 0) {
    throw new Error('S3_MAX_CONNECTIONS must be greater than 0');
  }
  
  if (config.connectionTimeout <= 0) {
    throw new Error('S3_CONNECTION_TIMEOUT must be greater than 0');
  }
};

// Validate configuration
validateS3Config(s3Config);

/**
 * Create S3 client configuration
 */
const createS3ClientConfig = (config: IS3Config): S3ClientConfig => {
  return {
    endpoint: config.endpoint,
    region: config.region,
    credentials: {
      accessKeyId: config.accessKeyId,
      secretAccessKey: config.secretAccessKey
    },
    forcePathStyle: config.forcePathStyle,
    maxAttempts: DEFAULT_S3_RETRY_CONFIG.maxAttempts,
    retryMode: DEFAULT_RETRY_MODE,
    requestHandler: new NodeHttpHandler({
      connectionTimeout: config.connectionTimeout,
      socketTimeout: config.connectionTimeout
    }),
    // Enable SSL by default for security
    tls: config.sslEnabled
  };
};

/**
 * Initialize S3 client
 */
const s3Client = new S3Client(createS3ClientConfig(s3Config));

/**
 * Get bucket configuration for the current environment
 * 
 * @returns The bucket configuration for the current environment
 */
const getBucketConfig = (): IBucketConfig => {
  return DEFAULT_BUCKET_CONFIGS[appConfig.env] || DEFAULT_BUCKET_CONFIGS.development;
};

/**
 * Helper function to create a key prefix for organizing files in S3
 * 
 * @param prefix - Optional custom prefix
 * @returns Formatted key prefix with trailing slash
 */
const createKeyPrefix = (prefix?: string): string => {
  if (!prefix) {
    // Default organization: YYYY/MM/DD/
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}/${month}/${day}/`;
  }
  
  // Ensure prefix ends with a slash
  return prefix.endsWith('/') ? prefix : `${prefix}/`;
};

/**
 * Get the appropriate bucket name based on environment
 * 
 * @param bucketName - Optional bucket name override
 * @returns The bucket name to use
 */
const getBucketName = (bucketName?: string): string => {
  return bucketName || s3Config.defaultBucket;
};

/**
 * Default server-side encryption configuration
 * Uses AES-256 encryption as required in the technical specification
 */
const DEFAULT_ENCRYPTION_CONFIG = {
  ServerSideEncryption: ServerSideEncryption.AES256
};

/**
 * Get the default storage options with AES-256 encryption
 * 
 * @returns Object with default storage options including encryption
 */
const getDefaultStorageOptions = () => {
  return {
    ServerSideEncryption: ServerSideEncryption.AES256,
    // Set appropriate ACL
    ACL: 'private',
    // Set appropriate storage class
    StorageClass: 'STANDARD',
    // Set cache control
    CacheControl: 'private, max-age=0, no-cache, no-store'
  };
};

export {
  s3Client,
  s3Config,
  getBucketConfig,
  getBucketName,
  createKeyPrefix,
  DEFAULT_S3_RETRY_CONFIG,
  DEFAULT_ENCRYPTION_CONFIG,
  getDefaultStorageOptions
};

export default s3Client;