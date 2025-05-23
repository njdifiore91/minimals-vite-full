/**
 * HMAC Signature Utilities
 * 
 * This file provides utilities for generating and verifying HMAC signatures for webhook payloads.
 * It implements HMAC-SHA256 signature generation with configurable secret keys, supports multiple
 * encoding formats (hex, base64), and includes verification functions to validate incoming webhook
 * signatures with timestamp-based expiration for enhanced security.
 */

import crypto from 'crypto';
import { signatureConfig } from '../config/webhook';

// ----------------------------------------------------------------------

/**
 * Supported hash algorithms for HMAC signatures
 */
export type HmacAlgorithm = 'sha256' | 'sha384' | 'sha512';

/**
 * Supported encoding formats for HMAC signatures
 */
export type HmacEncoding = 'hex' | 'base64' | 'base64url';

/**
 * Options for generating HMAC signatures
 */
export interface HmacSignatureOptions {
  /** Secret key used for signature generation */
  secretKey: string;
  /** Algorithm to use for signature generation (default: sha256) */
  algorithm?: HmacAlgorithm;
  /** Encoding format for the signature (default: hex) */
  encoding?: HmacEncoding;
  /** Whether to include a timestamp in the signature (default: true) */
  includeTimestamp?: boolean;
  /** Custom timestamp to use (default: current time) */
  timestamp?: number;
}

/**
 * Options for verifying HMAC signatures
 */
export interface HmacVerifyOptions extends HmacSignatureOptions {
  /** Maximum age of a signature in milliseconds (default: 5 minutes) */
  maxAge?: number;
}

/**
 * Result of a signature verification
 */
export interface SignatureVerificationResult {
  /** Whether the signature is valid */
  isValid: boolean;
  /** Reason for invalid signature, if applicable */
  reason?: 'invalid_signature' | 'expired_signature' | 'invalid_format';
  /** Timestamp extracted from the signature, if available */
  timestamp?: number;
  /** Age of the signature in milliseconds, if timestamp is available */
  age?: number;
}

// ----------------------------------------------------------------------

/**
 * Generates an HMAC signature for the provided payload
 * 
 * @param payload - The data to sign (object or string)
 * @param options - Signature generation options
 * @returns The generated signature
 */
export function generateSignature(
  payload: Record<string, any> | string,
  options: HmacSignatureOptions
): string {
  const {
    secretKey,
    algorithm = 'sha256',
    encoding = 'hex',
    includeTimestamp = true,
    timestamp = Date.now(),
  } = options;

  // Convert payload to string if it's an object
  const payloadString = typeof payload === 'string' ? payload : JSON.stringify(payload);

  // Create the string to sign
  const stringToSign = includeTimestamp ? `${timestamp}.${payloadString}` : payloadString;

  // Generate the HMAC signature
  const hmac = crypto.createHmac(algorithm, secretKey);
  hmac.update(stringToSign);

  // Return the signature in the specified encoding
  return hmac.digest(encoding);
}

/**
 * Generates a complete signature header value including timestamp
 * 
 * @param payload - The data to sign (object or string)
 * @param options - Signature generation options
 * @returns The complete signature header value
 */
export function generateSignatureHeader(
  payload: Record<string, any> | string,
  options: HmacSignatureOptions
): string {
  const {
    includeTimestamp = true,
    timestamp = Date.now(),
  } = options;

  const signature = generateSignature(payload, options);

  // Format the signature header value
  if (includeTimestamp) {
    return `t=${timestamp},v1=${signature}`;
  }
  
  return `v1=${signature}`;
}

/**
 * Verifies an HMAC signature against a payload
 * 
 * @param payload - The data that was signed (object or string)
 * @param signature - The signature to verify
 * @param options - Signature verification options
 * @returns The verification result
 */
export function verifySignature(
  payload: Record<string, any> | string,
  signature: string,
  options: HmacVerifyOptions
): SignatureVerificationResult {
  const {
    secretKey,
    algorithm = 'sha256',
    encoding = 'hex',
    includeTimestamp = true,
    maxAge = 5 * 60 * 1000, // 5 minutes default
  } = options;

  // Parse the signature to extract timestamp if included
  let signatureValue = signature;
  let timestamp: number | undefined;

  // Check if the signature includes a timestamp (t=timestamp,v1=signature format)
  if (signature.includes(',v1=')) {
    const match = signature.match(/t=([0-9]+),v1=(.+)/);
    if (match) {
      timestamp = parseInt(match[1], 10);
      signatureValue = match[2];
    } else {
      return { isValid: false, reason: 'invalid_format' };
    }
  } else if (signature.startsWith('v1=')) {
    // v1=signature format without timestamp
    signatureValue = signature.substring(3);
  }

  // If we're expecting a timestamp but didn't find one, use the provided timestamp
  if (includeTimestamp && !timestamp && options.timestamp) {
    timestamp = options.timestamp;
  }

  // Check if the signature has expired
  if (timestamp && maxAge > 0) {
    const age = Date.now() - timestamp;
    if (age > maxAge) {
      return { isValid: false, reason: 'expired_signature', timestamp, age };
    }
  }

  // Generate the expected signature
  const expectedSignature = generateSignature(payload, {
    secretKey,
    algorithm,
    encoding,
    includeTimestamp: !!timestamp,
    timestamp,
  });

  // Use a constant-time comparison to prevent timing attacks
  try {
    let isValid: boolean;

    if (encoding === 'hex') {
      const signatureBuffer = Buffer.from(signatureValue, 'hex');
      const expectedBuffer = Buffer.from(expectedSignature, 'hex');
      isValid = signatureBuffer.length === expectedBuffer.length &&
               crypto.timingSafeEqual(signatureBuffer, expectedBuffer);
    } else if (encoding === 'base64' || encoding === 'base64url') {
      const signatureBuffer = Buffer.from(signatureValue, encoding);
      const expectedBuffer = Buffer.from(expectedSignature, encoding);
      isValid = signatureBuffer.length === expectedBuffer.length &&
               crypto.timingSafeEqual(signatureBuffer, expectedBuffer);
    } else {
      // For other encodings, use a simple string comparison (less secure)
      isValid = signatureValue === expectedSignature;
    }

    return { 
      isValid, 
      timestamp, 
      age: timestamp ? Date.now() - timestamp : undefined 
    };
  } catch (error) {
    // If there's an error (e.g., invalid hex string), the signature is invalid
    return { isValid: false, reason: 'invalid_format' };
  }
}

/**
 * Extracts a signature from request headers
 * 
 * @param headers - The request headers
 * @param signatureHeaderName - The name of the header containing the signature
 * @param timestampHeaderName - The name of the header containing the timestamp (if separate)
 * @returns The extracted signature and timestamp
 */
export function extractSignatureFromHeaders(
  headers: Record<string, string | string[] | undefined>,
  signatureHeaderName: string = signatureConfig.headerName,
  timestampHeaderName: string = signatureConfig.timestampHeaderName
): { signature: string | null; timestamp: number | null } {
  // Get the signature header
  const signatureHeader = headers[signatureHeaderName] || headers[signatureHeaderName.toLowerCase()];
  if (!signatureHeader) {
    return { signature: null, timestamp: null };
  }

  const signature = Array.isArray(signatureHeader) ? signatureHeader[0] : signatureHeader;

  // Check if the signature includes a timestamp
  if (signature.includes(',v1=')) {
    const match = signature.match(/t=([0-9]+),v1=(.+)/);
    if (match) {
      return { signature: match[2], timestamp: parseInt(match[1], 10) };
    }
  }

  // Check for a separate timestamp header
  const timestampHeader = headers[timestampHeaderName] || headers[timestampHeaderName.toLowerCase()];
  let timestamp: number | null = null;
  
  if (timestampHeader) {
    const timestampValue = Array.isArray(timestampHeader) ? timestampHeader[0] : timestampHeader;
    timestamp = parseInt(timestampValue, 10) || null;
  }

  // If the signature starts with v1=, remove the prefix
  const cleanSignature = signature.startsWith('v1=') ? signature.substring(3) : signature;

  return { signature: cleanSignature, timestamp };
}

/**
 * Verifies a signature from request headers against a payload
 * 
 * @param payload - The data that was signed (object or string)
 * @param headers - The request headers
 * @param options - Signature verification options
 * @returns The verification result
 */
export function verifySignatureFromHeaders(
  payload: Record<string, any> | string,
  headers: Record<string, string | string[] | undefined>,
  options: HmacVerifyOptions
): SignatureVerificationResult {
  const { signature, timestamp } = extractSignatureFromHeaders(
    headers,
    options.signatureHeaderName || signatureConfig.headerName,
    options.timestampHeaderName || signatureConfig.timestampHeaderName
  );

  if (!signature) {
    return { isValid: false, reason: 'invalid_format' };
  }

  return verifySignature(payload, signature, {
    ...options,
    timestamp: timestamp || options.timestamp,
  });
}

/**
 * Creates a signature validator function with predefined options
 * 
 * @param options - Default signature verification options
 * @returns A function that verifies signatures with the predefined options
 */
export function createSignatureValidator(options: HmacVerifyOptions) {
  return (payload: Record<string, any> | string, signature: string, overrideOptions?: Partial<HmacVerifyOptions>) => {
    return verifySignature(payload, signature, { ...options, ...overrideOptions });
  };
}

/**
 * Creates a header signature validator function with predefined options
 * 
 * @param options - Default signature verification options
 * @returns A function that verifies signatures from headers with the predefined options
 */
export function createHeaderSignatureValidator(options: HmacVerifyOptions) {
  return (payload: Record<string, any> | string, headers: Record<string, string | string[] | undefined>, overrideOptions?: Partial<HmacVerifyOptions>) => {
    return verifySignatureFromHeaders(payload, headers, { ...options, ...overrideOptions });
  };
}