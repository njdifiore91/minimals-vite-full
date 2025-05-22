/**
 * HMAC Signature Utilities
 * 
 * This module provides utilities for generating and verifying HMAC-SHA256 signatures
 * for webhook payloads. It implements security measures to ensure the authenticity
 * and integrity of webhook communications as specified in section 3.8.5 of the
 * technical specification.
 */

import crypto from 'crypto';

/**
 * Supported encoding formats for HMAC signatures
 */
export enum HmacEncoding {
  HEX = 'hex',
  BASE64 = 'base64'
}

/**
 * Options for generating HMAC signatures
 */
export interface HmacSignatureOptions {
  /** Secret key used for signing */
  secretKey: string;
  /** Encoding format for the signature output */
  encoding?: HmacEncoding;
  /** Include timestamp in the signature to prevent replay attacks */
  includeTimestamp?: boolean;
  /** Custom algorithm (defaults to sha256) */
  algorithm?: string;
}

/**
 * Options for verifying HMAC signatures
 */
export interface HmacVerifyOptions extends HmacSignatureOptions {
  /** Maximum age of signature in milliseconds before it's considered expired */
  maxAge?: number;
}

/**
 * Result of signature verification
 */
export interface VerificationResult {
  /** Whether the signature is valid */
  isValid: boolean;
  /** Error message if validation failed */
  error?: string;
  /** Timestamp extracted from the signature (if included) */
  timestamp?: number;
}

/**
 * Default options for HMAC operations
 */
const DEFAULT_OPTIONS: HmacSignatureOptions = {
  secretKey: '',
  encoding: HmacEncoding.HEX,
  includeTimestamp: true,
  algorithm: 'sha256'
};

/**
 * Default verification options
 */
const DEFAULT_VERIFY_OPTIONS: HmacVerifyOptions = {
  ...DEFAULT_OPTIONS,
  maxAge: 5 * 60 * 1000 // 5 minutes in milliseconds
};

/**
 * Generates an HMAC signature for the provided payload
 * 
 * @param payload - The data to sign (object or string)
 * @param options - Signature generation options
 * @returns The generated signature string
 */
export function generateSignature(
  payload: Record<string, any> | string,
  options: HmacSignatureOptions
): string {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  
  // Convert payload to string if it's an object
  const stringPayload = typeof payload === 'string' 
    ? payload 
    : JSON.stringify(payload);
  
  // Create HMAC instance
  const hmac = crypto.createHmac(opts.algorithm, opts.secretKey);
  
  // Add timestamp if requested (helps prevent replay attacks)
  const timestamp = opts.includeTimestamp ? Date.now() : null;
  const dataToSign = timestamp 
    ? `${timestamp}.${stringPayload}` 
    : stringPayload;
  
  // Generate signature
  return hmac.update(dataToSign).digest(opts.encoding);
}

/**
 * Verifies an HMAC signature against a payload
 * 
 * @param payload - The data that was signed (object or string)
 * @param signature - The signature to verify
 * @param options - Verification options
 * @returns Verification result with validity and error information
 */
export function verifySignature(
  payload: Record<string, any> | string,
  signature: string,
  options: HmacVerifyOptions
): VerificationResult {
  const opts = { ...DEFAULT_VERIFY_OPTIONS, ...options };
  
  // Handle empty signature
  if (!signature) {
    return { isValid: false, error: 'Signature is missing' };
  }
  
  // Convert payload to string if it's an object
  const stringPayload = typeof payload === 'string' 
    ? payload 
    : JSON.stringify(payload);
  
  try {
    // Check if signature contains timestamp
    let timestamp: number | null = null;
    let dataToVerify = stringPayload;
    
    if (opts.includeTimestamp) {
      // Try to extract timestamp from signature
      const parts = signature.split('.');
      if (parts.length === 2) {
        timestamp = parseInt(parts[0], 10);
        signature = parts[1];
        
        // Check if timestamp is valid
        if (isNaN(timestamp)) {
          return { isValid: false, error: 'Invalid timestamp format in signature' };
        }
        
        // Check if signature is expired
        const now = Date.now();
        if (now - timestamp > opts.maxAge) {
          return { 
            isValid: false, 
            error: 'Signature has expired', 
            timestamp 
          };
        }
        
        dataToVerify = `${timestamp}.${stringPayload}`;
      }
    }
    
    // Generate expected signature
    const hmac = crypto.createHmac(opts.algorithm, opts.secretKey);
    const expectedSignature = hmac.update(dataToVerify).digest(opts.encoding);
    
    // Use timing-safe comparison to prevent timing attacks
    const expectedBuffer = Buffer.from(expectedSignature, opts.encoding);
    const providedBuffer = Buffer.from(signature, opts.encoding);
    
    // Ensure buffers are the same length for comparison
    if (expectedBuffer.length !== providedBuffer.length) {
      return { isValid: false, error: 'Invalid signature length' };
    }
    
    const isValid = crypto.timingSafeEqual(expectedBuffer, providedBuffer);
    
    return { 
      isValid, 
      timestamp,
      error: isValid ? undefined : 'Signature verification failed'
    };
  } catch (error) {
    return { 
      isValid: false, 
      error: `Signature verification error: ${error.message}` 
    };
  }
}

/**
 * Extracts the HMAC signature from request headers
 * 
 * @param headers - HTTP headers object
 * @param headerName - Name of the header containing the signature
 * @returns The extracted signature or null if not found
 */
export function extractSignatureFromHeaders(
  headers: Record<string, string | string[] | undefined>,
  headerName: string = 'x-webhook-signature'
): string | null {
  const normalizedHeaderName = headerName.toLowerCase();
  const headerValue = headers[normalizedHeaderName] || headers[headerName];
  
  if (!headerValue) {
    return null;
  }
  
  return Array.isArray(headerValue) ? headerValue[0] : headerValue;
}

/**
 * Verifies a webhook payload using the signature in the headers
 * 
 * @param payload - The webhook payload to verify
 * @param headers - HTTP headers containing the signature
 * @param options - Verification options
 * @param headerName - Name of the header containing the signature
 * @returns Verification result
 */
export function verifyWebhookSignature(
  payload: Record<string, any> | string,
  headers: Record<string, string | string[] | undefined>,
  options: HmacVerifyOptions,
  headerName: string = 'x-webhook-signature'
): VerificationResult {
  const signature = extractSignatureFromHeaders(headers, headerName);
  
  if (!signature) {
    return { isValid: false, error: `Signature header '${headerName}' not found` };
  }
  
  return verifySignature(payload, signature, options);
}