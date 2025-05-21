/**
 * S3 Configuration for Email Service
 * 
 * This file configures the S3-compatible storage client for the Email Service to store email attachments.
 * It defines connection parameters, bucket settings, encryption options, and access controls.
 * It enables the service to securely store and retrieve email attachments from the document repository.
 */

import { 
  S3Client, 
  PutObjectCommand, 
  GetObjectCommand,
  DeleteObjectCommand,
  HeadObjectCommand,
  ServerSideEncryption,
  S3ClientConfig,
  S3ServiceException
} from '@aws-sdk/client-s3';
import { NodeHttpHandler } from '@aws-sdk/node-http-handler';
import { Logger } from './logger';
import { appConfig } from './app';

/**
 * Interface for S3 bucket configuration
 */
interface S3BucketConfig {
  name: string;
  region: string;
  prefix: string;
}

/**
 * Interface for S3 service configuration
 */
interface S3Config {
  endpoint: string;
  region: string;
  credentials: {
    accessKeyId: string;
    secretAccessKey: string;
  };
  buckets: {
    production: S3BucketConfig;
    staging: S3BucketConfig;
    development: S3BucketConfig;
  };
  encryption: {
    serverSideEncryption: ServerSideEncryption;
  };
  connectionOptions: {
    timeout: number;
    maxAttempts: number;
  };
}

/**
 * S3 configuration object
 */
export const s3Config: S3Config = {
  endpoint: appConfig.s3.endpoint,
  region: appConfig.s3.region,
  credentials: {
    accessKeyId: appConfig.s3.accessKeyId,
    secretAccessKey: appConfig.s3.secretAccessKey,
  },
  buckets: {
    production: {
      name: 'mca-documents-production',
      region: appConfig.s3.region,
      prefix: 'email-attachments/'
    },
    staging: {
      name: 'mca-documents-staging',
      region: appConfig.s3.region,
      prefix: 'email-attachments/'
    },
    development: {
      name: 'mca-documents-development',
      region: appConfig.s3.region,
      prefix: 'email-attachments/'
    }
  },
  encryption: {
    // AES-256 encryption for all stored objects
    serverSideEncryption: 'AES256'
  },
  connectionOptions: {
    timeout: 30000, // 30 seconds
    maxAttempts: 3
  }
};

/**
 * Get the current bucket configuration based on the environment
 */
export const getCurrentBucket = (): S3BucketConfig => {
  const env = appConfig.environment;
  
  switch (env) {
    case 'production':
      return s3Config.buckets.production;
    case 'staging':
      return s3Config.buckets.staging;
    case 'development':
    default:
      return s3Config.buckets.development;
  }
};

/**
 * Create S3 client configuration
 */
const createS3ClientConfig = (): S3ClientConfig => {
  const config: S3ClientConfig = {
    region: s3Config.region,
    credentials: {
      accessKeyId: s3Config.credentials.accessKeyId,
      secretAccessKey: s3Config.credentials.secretAccessKey,
    },
    requestHandler: new NodeHttpHandler({
      connectionTimeout: s3Config.connectionOptions.timeout,
      socketTimeout: s3Config.connectionOptions.timeout
    }),
    maxAttempts: s3Config.connectionOptions.maxAttempts
  };

  // If a custom endpoint is provided (for local development or testing)
  if (s3Config.endpoint) {
    config.endpoint = s3Config.endpoint;
    // Force path style for custom endpoints
    config.forcePathStyle = true;
  }

  return config;
};

/**
 * Initialize S3 client
 */
export const s3Client = new S3Client(createS3ClientConfig());

/**
 * Handle S3 service exceptions
 * @param error - The error to handle
 * @param operation - The operation that caused the error
 */
export const handleS3Error = (error: unknown, operation: string): void => {
  if (error instanceof S3ServiceException) {
    Logger.error(`S3 ${operation} operation failed: ${error.name} - ${error.message}`, {
      errorCode: error.$metadata.httpStatusCode,
      requestId: error.$metadata.requestId,
      operation
    });
  } else {
    Logger.error(`Unexpected error during S3 ${operation} operation: ${String(error)}`, {
      operation
    });
  }
};

/**
 * Generate a unique key for storing an attachment in S3
 * @param emailId - The ID of the email
 * @param filename - The original filename of the attachment
 * @returns The S3 key for the attachment
 */
export const generateAttachmentKey = (emailId: string, filename: string): string => {
  const currentBucket = getCurrentBucket();
  const timestamp = new Date().getTime();
  const sanitizedFilename = filename.replace(/[^a-zA-Z0-9._-]/g, '_');
  
  return `${currentBucket.prefix}${emailId}/${timestamp}-${sanitizedFilename}`;
};

/**
 * Default S3 put object parameters with encryption
 */
export const getDefaultPutObjectParams = () => ({
  ServerSideEncryption: s3Config.encryption.serverSideEncryption,
  Bucket: getCurrentBucket().name
});

export default {
  s3Client,
  s3Config,
  getCurrentBucket,
  handleS3Error,
  generateAttachmentKey,
  getDefaultPutObjectParams
};