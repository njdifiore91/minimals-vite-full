/**
 * HMAC Signature Verification Middleware
 * 
 * This middleware validates the authenticity and integrity of webhook payloads
 * by verifying HMAC-SHA256 signatures. It ensures that webhook payloads are not
 * tampered with during transmission and that they originate from trusted sources.
 * 
 * Features:
 * - HMAC-SHA256 signature verification
 * - Timestamp validation to prevent replay attacks
 * - Customer-specific secret key management
 * - Detailed error responses for verification failures
 * - Configurable options for header names and validation rules
 */

import { Request, Response, NextFunction } from 'express';
import crypto from 'crypto';
import { getErrorMessage } from '../utils/error-message';

/**
 * Extended Express Request interface with HMAC verification result
 */
declare global {
  namespace Express {
    interface Request {
      /**
       * HMAC verification result for the current request
       */
      hmacVerification?: {
        /**
         * Whether the signature is valid
         */
        isValid: boolean;
        
        /**
         * Timestamp from the signature header (if available)
         */
        timestamp?: number;
        
        /**
         * Customer ID associated with the secret key used for verification
         */
        customerId?: string;
      };
    }
  }
}

/**
 * Configuration options for the HMAC verification middleware
 */
export interface HmacVerificationOptions {
  /**
   * Header name containing the HMAC signature
   * @default 'X-Signature-SHA256'
   */
  signatureHeaderName?: string;
  
  /**
   * Header name containing the timestamp (if separate from signature)
   * @default 'X-Signature-Timestamp'
   */
  timestampHeaderName?: string;
  
  /**
   * Whether to require a timestamp in the request
   * @default true
   */
  requireTimestamp?: boolean;
  
  /**
   * Maximum age of the timestamp in seconds (to prevent replay attacks)
   * @default 300 (5 minutes)
   */
  maxTimestampAge?: number;
  
  /**
   * Function to retrieve the secret key for a given customer ID
   * If not provided, the middleware will use the default secret key
   */
  getSecretKey?: (customerId: string) => Promise<string | null>;
  
  /**
   * Default secret key to use if getSecretKey is not provided or returns null
   * Required if getSecretKey is not provided
   */
  defaultSecretKey?: string;
  
  /**
   * Function to extract customer ID from the request
   * If not provided, the middleware will look for a customer_id query parameter
   */
  getCustomerId?: (req: Request) => string | null;
  
  /**
   * Whether to allow requests to proceed when signature verification fails
   * @default false
   */
  allowOnFailure?: boolean;
  
  /**
   * Whether to skip verification for certain requests
   * @default () => false
   */
  skipVerification?: (req: Request) => boolean;
}

/**
 * Default HMAC verification options
 */
const defaultOptions: HmacVerificationOptions = {
  signatureHeaderName: 'X-Signature-SHA256',
  timestampHeaderName: 'X-Signature-Timestamp',
  requireTimestamp: true,
  maxTimestampAge: 300, // 5 minutes
  allowOnFailure: false,
  skipVerification: () => false
};

/**
 * Parse signature header value
 * 
 * Handles different signature formats:
 * - Plain hex string: The entire header value is the signature
 * - t=timestamp,v1=signature: Extracts timestamp and signature from the header
 * 
 * @param headerValue The signature header value
 * @returns Parsed signature and timestamp (if available)
 */
function parseSignatureHeader(headerValue: string): { signature: string; timestamp?: number } {
  // Check if the header follows the t=timestamp,v1=signature format
  const timestampMatch = headerValue.match(/t=([0-9]+)/);
  const signatureMatch = headerValue.match(/v1=([a-f0-9]+)/i);
  
  if (timestampMatch && signatureMatch) {
    return {
      signature: signatureMatch[1],
      timestamp: parseInt(timestampMatch[1], 10)
    };
  }
  
  // If no matches, assume the entire header is the signature
  return { signature: headerValue };
}

/**
 * Verify HMAC signature for a request
 * 
 * @param req Express request object
 * @param rawBody Raw request body buffer
 * @param secretKey Secret key for HMAC verification
 * @param options Middleware options
 * @returns Verification result with isValid flag
 */
async function verifySignature(
  req: Request,
  rawBody: Buffer,
  secretKey: string,
  options: HmacVerificationOptions
): Promise<{ isValid: boolean; timestamp?: number; error?: string }> {
  try {
    // Get signature from header
    const signatureHeader = req.get(options.signatureHeaderName);
    if (!signatureHeader) {
      return { isValid: false, error: `Missing ${options.signatureHeaderName} header` };
    }
    
    // Parse signature header
    const { signature: receivedSignature, timestamp: headerTimestamp } = parseSignatureHeader(signatureHeader);
    
    // Get timestamp (either from signature header or separate header)
    let timestamp = headerTimestamp;
    if (!timestamp && options.requireTimestamp) {
      const timestampHeader = req.get(options.timestampHeaderName);
      if (timestampHeader) {
        timestamp = parseInt(timestampHeader, 10);
      }
    }
    
    // Validate timestamp if required
    if (options.requireTimestamp && (!timestamp || isNaN(timestamp))) {
      return { isValid: false, error: 'Missing or invalid timestamp' };
    }
    
    // Check timestamp age to prevent replay attacks
    if (timestamp && options.maxTimestampAge) {
      const currentTime = Math.floor(Date.now() / 1000);
      const timestampAge = currentTime - timestamp;
      
      if (timestampAge < 0) {
        return { isValid: false, timestamp, error: 'Timestamp is in the future' };
      }
      
      if (timestampAge > options.maxTimestampAge) {
        return { 
          isValid: false, 
          timestamp, 
          error: `Timestamp expired (age: ${timestampAge}s, max: ${options.maxTimestampAge}s)` 
        };
      }
    }
    
    // Create payload for signature verification
    let payload: Buffer;
    if (timestamp) {
      // If timestamp is available, include it in the payload
      payload = Buffer.concat([
        Buffer.from(timestamp.toString()),
        Buffer.from('.'),
        rawBody
      ]);
    } else {
      // Otherwise, just use the raw body
      payload = rawBody;
    }
    
    // Calculate expected signature
    const hmac = crypto.createHmac('sha256', secretKey);
    hmac.update(payload);
    const expectedSignature = hmac.digest('hex');
    
    // Compare signatures using constant-time comparison to prevent timing attacks
    const receivedBuffer = Buffer.from(receivedSignature, 'hex');
    const expectedBuffer = Buffer.from(expectedSignature, 'hex');
    
    // Ensure both buffers have the same length before comparison
    if (receivedBuffer.length !== expectedBuffer.length) {
      return { isValid: false, timestamp, error: 'Invalid signature length' };
    }
    
    const isValid = crypto.timingSafeEqual(receivedBuffer, expectedBuffer);
    return { isValid, timestamp };
  } catch (error) {
    return { isValid: false, error: `Signature verification error: ${getErrorMessage(error)}` };
  }
}

/**
 * Extract raw body from request
 * 
 * @param req Express request object
 * @returns Raw request body as Buffer
 */
function getRawBody(req: Request): Buffer | null {
  // If the raw body was saved by body-parser or similar middleware
  if ((req as any).rawBody) {
    return Buffer.from((req as any).rawBody);
  }
  
  // If the body was parsed as JSON, stringify it back
  if (req.body) {
    return Buffer.from(JSON.stringify(req.body));
  }
  
  return null;
}

/**
 * Create HMAC signature verification middleware
 * 
 * @param options Configuration options for the middleware
 * @returns Express middleware function
 */
export default function hmacVerificationMiddleware(options: HmacVerificationOptions = {}) {
  // Merge provided options with defaults
  const config = { ...defaultOptions, ...options };
  
  // Validate configuration
  if (!config.getSecretKey && !config.defaultSecretKey) {
    throw new Error('Either getSecretKey or defaultSecretKey must be provided');
  }
  
  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      // Skip verification if configured to do so
      if (config.skipVerification && config.skipVerification(req)) {
        return next();
      }
      
      // Get raw request body
      const rawBody = getRawBody(req);
      if (!rawBody) {
        if (config.allowOnFailure) {
          req.hmacVerification = { isValid: false };
          return next();
        }
        return res.status(400).json({ error: 'Request body is required for HMAC verification' });
      }
      
      // Get customer ID for secret key lookup
      let customerId: string | null = null;
      if (config.getCustomerId) {
        customerId = config.getCustomerId(req);
      } else {
        customerId = req.query.customer_id as string || null;
      }
      
      // Get secret key for verification
      let secretKey: string;
      if (customerId && config.getSecretKey) {
        secretKey = await config.getSecretKey(customerId) || config.defaultSecretKey;
      } else {
        secretKey = config.defaultSecretKey;
      }
      
      if (!secretKey) {
        if (config.allowOnFailure) {
          req.hmacVerification = { isValid: false };
          return next();
        }
        return res.status(401).json({ error: 'No secret key available for HMAC verification' });
      }
      
      // Verify signature
      const result = await verifySignature(req, rawBody, secretKey, config);
      
      // Add verification result to request for use in route handlers
      req.hmacVerification = {
        isValid: result.isValid,
        timestamp: result.timestamp,
        customerId: customerId || undefined
      };
      
      // Handle verification failure
      if (!result.isValid) {
        if (config.allowOnFailure) {
          return next();
        }
        return res.status(401).json({ 
          error: 'HMAC signature verification failed', 
          details: result.error 
        });
      }
      
      // Continue with request handling
      next();
    } catch (error) {
      // Handle unexpected errors
      if (config.allowOnFailure) {
        req.hmacVerification = { isValid: false };
        return next();
      }
      return res.status(500).json({ 
        error: 'HMAC verification error', 
        message: getErrorMessage(error) 
      });
    }
  };
}

/**
 * Express middleware that requires a valid HMAC signature
 * This is a convenience wrapper around hmacVerificationMiddleware
 * that always rejects requests with invalid signatures
 * 
 * @param options Configuration options for the middleware
 * @returns Express middleware function
 */
export function requireValidHmacSignature(options: HmacVerificationOptions = {}) {
  return hmacVerificationMiddleware({
    ...options,
    allowOnFailure: false
  });
}

/**
 * Express middleware that checks but doesn't require a valid HMAC signature
 * This is a convenience wrapper around hmacVerificationMiddleware
 * that allows requests to proceed even with invalid signatures
 * 
 * @param options Configuration options for the middleware
 * @returns Express middleware function
 */
export function checkHmacSignature(options: HmacVerificationOptions = {}) {
  return hmacVerificationMiddleware({
    ...options,
    allowOnFailure: true
  });
}