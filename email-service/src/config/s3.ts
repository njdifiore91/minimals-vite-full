/**
 * @file s3.ts
 * @description Configures the S3-compatible storage client for the Email Service
 * to store email attachments. This file defines connection parameters, bucket settings,
 * encryption options, and access controls.
 */

import { IS3Config, IBucketEnvironmentConfig } from '../types/storage';

/**
 * Environment-specific bucket configurations
 */
export const bucketConfig: IBucketEnvironmentConfig = {
  production: {
    name: 'mca-documents-production',
    region: 'us-east-1',
    versioning: true,
    lifecycleRules: [
      {
        id: 'archive-rule',
        prefix: 'documents/',
        transitionDays: 90,
        storageClass: 'GLACIER',
      },
    ],
  },
  staging: {
    name: 'mca-documents-staging',
    region: 'us-east-1',
    versioning: true,
    lifecycleRules: [
      {
        id: 'expire-rule',
        prefix: 'documents/',
        expirationDays: 30,
      },
    ],
  },
  development: {
    name: 'mca-documents-development',
    region: 'us-east-1',
    versioning: false,
    lifecycleRules: [
      {
        id: 'expire-rule',
        prefix: 'documents/',
        expirationDays: 7,
      },
    ],
  },
};

/**
 * Creates an S3 configuration object from environment variables
 * @returns S3 configuration object
 */
export const createS3ConfigFromEnv = (): IS3Config => {
  // Validate required environment variables
  const requiredEnvVars = [
    'S3_ENDPOINT',
    'S3_REGION',
    'S3_ACCESS_KEY',
    'S3_SECRET_KEY',
  ];

  for (const envVar of requiredEnvVars) {
    if (!process.env[envVar]) {
      throw new Error(`Missing required environment variable: ${envVar}`);
    }
  }

  // Parse boolean environment variables
  const useSSL = process.env.S3_USE_SSL !== 'false'; // Default to true
  const forcePathStyle = process.env.S3_FORCE_PATH_STYLE === 'true'; // Default to false
  const encryptionEnabled = process.env.S3_ENCRYPTION_ENABLED !== 'false'; // Default to true

  // Parse numeric environment variables
  const uploadTimeout = parseInt(process.env.S3_UPLOAD_TIMEOUT || '60000', 10);
  const downloadTimeout = parseInt(process.env.S3_DOWNLOAD_TIMEOUT || '60000', 10);
  const maxRetries = parseInt(process.env.MAX_RETRY_ATTEMPTS || '3', 10);

  // Construct the endpoint URL with the correct protocol
  const endpoint = process.env.S3_ENDPOINT!.startsWith('http')
    ? process.env.S3_ENDPOINT!
    : `${useSSL ? 'https' : 'http'}://${process.env.S3_ENDPOINT}`;

  // Create and return the configuration object
  return {
    endpoint,
    region: process.env.S3_REGION!,
    credentials: {
      accessKeyId: process.env.S3_ACCESS_KEY!,
      secretAccessKey: process.env.S3_SECRET_KEY!,
    },
    forcePathStyle,
    maxRetries,
    connectionTimeout: uploadTimeout,
    socketTimeout: downloadTimeout,
  };
};

/**
 * Gets the appropriate bucket name based on the current environment
 * @returns Bucket name for the current environment
 */
export const getBucketForCurrentEnv = (): string => {
  const env = (process.env.NODE_ENV || 'development') as keyof IBucketEnvironmentConfig;
  
  // Default to development if the environment is not recognized
  if (!bucketConfig[env]) {
    return bucketConfig.development.name;
  }
  
  return bucketConfig[env].name;
};

/**
 * Validates that the S3 bucket exists and is accessible
 * @param s3Client S3 client instance
 * @param bucketName Bucket name to validate
 * @returns Promise resolving to true if the bucket is accessible
 */
export const validateBucketAccess = async (
  s3Client: any,
  bucketName: string
): Promise<boolean> => {
  try {
    // Import dynamically to avoid circular dependencies
    const { HeadBucketCommand } = await import('@aws-sdk/client-s3');
    
    await s3Client.send(new HeadBucketCommand({ Bucket: bucketName }));
    return true;
  } catch (error) {
    console.error(`Error validating bucket access for ${bucketName}:`, error);
    return false;
  }
};