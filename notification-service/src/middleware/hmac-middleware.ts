/**
 * HMAC Signature Verification Middleware
 * 
 * This middleware validates the authenticity and integrity of webhook payloads
 * by verifying HMAC-SHA256 signatures. It ensures that webhook payloads are not
 * tampered with during transmission and that they originate from trusted sources.
 * 
 * As specified in section 3.8.5 of the technical specification, all webhook payloads
 * must be signed using HMAC-SHA256 with customer-specific secret keys.
 */

import { Request, Response, NextFunction } from 'express';
import { getErrorMessage } from '../../src/auth/utils/error-message';
import { 
  verifyWebhookSignature, 
  extractSignatureFromHeaders,
  HmacVerifyOptions 
} from '../utils/hmac';

/**
 * Configuration options for the HMAC middleware
 */
export interface HmacMiddlewareOptions {
  /** 
   * Function to retrieve the secret key for a specific customer or webhook
   * This allows dynamic secret key lookup based on request parameters
   */
  getSecretKey: (req: Request) => Promise<string> | string;
  
  /** Name of the header containing the HMAC signature */
  signatureHeaderName?: string;
  
  /** Maximum age of signature in milliseconds before it's considered expired */
  maxAge?: number;
  
  /** Whether to include timestamp validation */
  includeTimestamp?: boolean;
  
  /** HMAC algorithm to use (defaults to sha256) */
  algorithm?: string;
  
  /** Whether to skip verification in development mode */
  skipInDevelopment?: boolean;
}

/**
 * Default options for the HMAC middleware
 */
const DEFAULT_OPTIONS: Partial<HmacMiddlewareOptions> = {
  signatureHeaderName: 'x-webhook-signature',
  maxAge: 5 * 60 * 1000, // 5 minutes in milliseconds
  includeTimestamp: true,
  algorithm: 'sha256',
  skipInDevelopment: false
};

/**
 * Creates an Express middleware function that verifies HMAC signatures on incoming requests
 * 
 * @param options - Configuration options for the middleware
 * @returns Express middleware function
 */
export function createHmacMiddleware(options: HmacMiddlewareOptions) {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  
  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      // Skip verification in development mode if configured
      if (opts.skipInDevelopment && process.env.NODE_ENV === 'development') {
        return next();
      }
      
      // Get the raw request body
      const payload = req.body;
      
      // If there's no body, there's nothing to verify
      if (!payload) {
        return res.status(400).json({
          statusCode: 400,
          message: 'Missing request body',
          errorCode: 'MISSING_BODY',
          correlationId: req.headers['x-correlation-id'] || 'unknown',
          timestamp: new Date().toISOString()
        });
      }
      
      // Extract the signature from headers
      const signature = extractSignatureFromHeaders(
        req.headers,
        opts.signatureHeaderName
      );
      
      if (!signature) {
        return res.status(401).json({
          statusCode: 401,
          message: `Missing signature header: ${opts.signatureHeaderName}`,
          errorCode: 'MISSING_SIGNATURE',
          correlationId: req.headers['x-correlation-id'] || 'unknown',
          timestamp: new Date().toISOString()
        });
      }
      
      // Get the secret key for this request
      const secretKey = await opts.getSecretKey(req);
      
      if (!secretKey) {
        return res.status(401).json({
          statusCode: 401,
          message: 'Unable to retrieve secret key for signature verification',
          errorCode: 'INVALID_SECRET_KEY',
          correlationId: req.headers['x-correlation-id'] || 'unknown',
          timestamp: new Date().toISOString()
        });
      }
      
      // Verify the signature
      const verifyOptions: HmacVerifyOptions = {
        secretKey,
        includeTimestamp: opts.includeTimestamp,
        algorithm: opts.algorithm,
        maxAge: opts.maxAge
      };
      
      const verificationResult = verifyWebhookSignature(
        payload,
        req.headers,
        verifyOptions,
        opts.signatureHeaderName
      );
      
      if (!verificationResult.isValid) {
        // Log the verification failure with details
        console.error('HMAC signature verification failed', {
          error: verificationResult.error,
          timestamp: verificationResult.timestamp,
          correlationId: req.headers['x-correlation-id'] || 'unknown',
          path: req.path
        });
        
        return res.status(401).json({
          statusCode: 401,
          message: verificationResult.error || 'Invalid signature',
          errorCode: 'INVALID_SIGNATURE',
          correlationId: req.headers['x-correlation-id'] || 'unknown',
          timestamp: new Date().toISOString()
        });
      }
      
      // If we get here, the signature is valid
      // Add verification result to request for downstream handlers
      req.hmacVerified = true;
      req.hmacTimestamp = verificationResult.timestamp;
      
      // Continue to the next middleware
      next();
    } catch (error) {
      // Handle any unexpected errors
      const errorMessage = getErrorMessage(error);
      
      console.error('Error in HMAC middleware', {
        error: errorMessage,
        stack: error instanceof Error ? error.stack : undefined,
        correlationId: req.headers['x-correlation-id'] || 'unknown',
        path: req.path
      });
      
      return res.status(500).json({
        statusCode: 500,
        message: 'Error verifying signature',
        errorCode: 'SIGNATURE_VERIFICATION_ERROR',
        correlationId: req.headers['x-correlation-id'] || 'unknown',
        timestamp: new Date().toISOString(),
        details: { error: errorMessage }
      });
    }
  };
}

/**
 * Extend Express Request interface to include HMAC verification properties
 */
declare global {
  namespace Express {
    interface Request {
      /** Whether the request has been verified by HMAC middleware */
      hmacVerified?: boolean;
      /** Timestamp extracted from the HMAC signature (if included) */
      hmacTimestamp?: number;
    }
  }
}