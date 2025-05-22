/**
 * Validation utilities for webhook configurations, notification payloads, and message formats.
 * This file implements schema validation, format checking, and data sanitization to ensure
 * consistent and secure data handling throughout the Notification Service.
 */

import Ajv, { ErrorObject } from 'ajv';
import addFormats from 'ajv-formats';
import { URL } from 'url';
import crypto from 'crypto';
import { 
  WebhookMethod, 
  IWebhookConfig, 
  IWebhookHeaders, 
  IWebhookPayload,
  IWebhookSignature,
  WebhookStatus
} from '../types/webhook';
import { 
  MessageChannel, 
  IMessagePayload, 
  MessageStatus 
} from '../types/message';
import { 
  NotificationType, 
  INotificationPayload, 
  NotificationStatus 
} from '../types/notification';

// Initialize JSON Schema validator
const ajv = new Ajv({ allErrors: true, removeAdditional: 'all', useDefaults: true });
addFormats(ajv);

/**
 * Error interface for validation errors
 */
export interface IValidationError {
  field: string;
  message: string;
  code?: string;
}

/**
 * Result interface for validation results
 */
export interface IValidationResult {
  valid: boolean;
  errors?: IValidationError[];
}

/**
 * Converts Ajv errors to a standardized validation error format
 * @param errors - Ajv error objects
 * @returns Array of standardized validation errors
 */
const formatAjvErrors = (errors: ErrorObject[] | null | undefined): IValidationError[] => {
  if (!errors || errors.length === 0) {
    return [];
  }

  return errors.map((error) => {
    const field = error.instancePath.replace(/^\//, '') || error.params.missingProperty || 'unknown';
    return {
      field,
      message: error.message || 'Invalid value',
      code: error.keyword
    };
  });
};

/**
 * Validates data against a JSON schema
 * @param schema - JSON schema to validate against
 * @param data - Data to validate
 * @returns Validation result with errors if invalid
 */
export const validateSchema = (schema: object, data: unknown): IValidationResult => {
  const validate = ajv.compile(schema);
  const valid = validate(data);

  if (!valid) {
    return {
      valid: false,
      errors: formatAjvErrors(validate.errors)
    };
  }

  return { valid: true };
};

/**
 * Validates a webhook payload against its schema
 * @param payload - Webhook payload to validate
 * @returns Validation result with errors if invalid
 */
export const validateWebhookPayload = (payload: IWebhookPayload): IValidationResult => {
  // This is a simplified example - in a real implementation, you would have
  // different schemas for different webhook types and select the appropriate one
  const webhookSchema = {
    type: 'object',
    required: ['event', 'data', 'timestamp'],
    properties: {
      event: { type: 'string' },
      data: { type: 'object' },
      timestamp: { type: 'string', format: 'date-time' },
      version: { type: 'string' }
    },
    additionalProperties: false
  };

  return validateSchema(webhookSchema, payload);
};

/**
 * Validates a URL string
 * @param url - URL string to validate
 * @returns Validation result with errors if invalid
 */
export const validateUrl = (url: string): IValidationResult => {
  try {
    // Attempt to create a URL object to validate the URL
    const urlObj = new URL(url);
    
    // Check for required protocol (http or https)
    if (!['http:', 'https:'].includes(urlObj.protocol)) {
      return {
        valid: false,
        errors: [{
          field: 'url',
          message: 'URL must use HTTP or HTTPS protocol',
          code: 'invalid_protocol'
        }]
      };
    }
    
    return { valid: true };
  } catch (error) {
    return {
      valid: false,
      errors: [{
        field: 'url',
        message: 'Invalid URL format',
        code: 'invalid_url'
      }]
    };
  }
};

/**
 * Validates webhook HTTP method
 * @param method - HTTP method to validate
 * @returns Validation result with errors if invalid
 */
export const validateWebhookMethod = (method: string): IValidationResult => {
  const validMethods = Object.values(WebhookMethod);
  
  if (!validMethods.includes(method as WebhookMethod)) {
    return {
      valid: false,
      errors: [{
        field: 'method',
        message: `Method must be one of: ${validMethods.join(', ')}`,
        code: 'invalid_method'
      }]
    };
  }
  
  return { valid: true };
};

/**
 * Validates webhook headers
 * @param headers - Headers to validate
 * @returns Validation result with errors if invalid
 */
export const validateWebhookHeaders = (headers: IWebhookHeaders): IValidationResult => {
  const headerSchema = {
    type: 'object',
    properties: {
      'Content-Type': { type: 'string' },
      'Authorization': { type: 'string' },
      'X-Signature': { type: 'string' }
    },
    additionalProperties: true
  };
  
  return validateSchema(headerSchema, headers);
};

/**
 * Validates a complete webhook configuration
 * @param config - Webhook configuration to validate
 * @returns Validation result with errors if invalid
 */
export const validateWebhookConfig = (config: IWebhookConfig): IValidationResult => {
  const errors: IValidationError[] = [];
  
  // Validate URL
  const urlResult = validateUrl(config.url);
  if (!urlResult.valid && urlResult.errors) {
    errors.push(...urlResult.errors);
  }
  
  // Validate method
  const methodResult = validateWebhookMethod(config.method);
  if (!methodResult.valid && methodResult.errors) {
    errors.push(...methodResult.errors);
  }
  
  // Validate headers if present
  if (config.headers) {
    const headersResult = validateWebhookHeaders(config.headers);
    if (!headersResult.valid && headersResult.errors) {
      errors.push(...headersResult.errors);
    }
  }
  
  // Check for required secret if signature verification is enabled
  if (config.signatureVerification && !config.secret) {
    errors.push({
      field: 'secret',
      message: 'Secret is required when signature verification is enabled',
      code: 'missing_secret'
    });
  }
  
  return errors.length > 0 ? { valid: false, errors } : { valid: true };
};

/**
 * Validates a notification payload
 * @param payload - Notification payload to validate
 * @returns Validation result with errors if invalid
 */
export const validateNotificationPayload = (payload: INotificationPayload): IValidationResult => {
  const notificationSchema = {
    type: 'object',
    required: ['type', 'content'],
    properties: {
      type: { type: 'string', enum: Object.values(NotificationType) },
      content: { type: 'object' },
      metadata: { type: 'object' }
    },
    additionalProperties: false
  };
  
  return validateSchema(notificationSchema, payload);
};

/**
 * Validates a message payload based on its channel
 * @param payload - Message payload to validate
 * @param channel - Message channel
 * @returns Validation result with errors if invalid
 */
export const validateMessagePayload = (payload: IMessagePayload, channel: MessageChannel): IValidationResult => {
  let messageSchema;
  
  switch (channel) {
    case MessageChannel.EMAIL:
      messageSchema = {
        type: 'object',
        required: ['to', 'subject', 'body'],
        properties: {
          to: { type: 'string', format: 'email' },
          cc: { type: 'array', items: { type: 'string', format: 'email' } },
          bcc: { type: 'array', items: { type: 'string', format: 'email' } },
          subject: { type: 'string', maxLength: 255 },
          body: { type: 'string' },
          isHtml: { type: 'boolean' }
        },
        additionalProperties: false
      };
      break;
      
    case MessageChannel.SMS:
      messageSchema = {
        type: 'object',
        required: ['to', 'body'],
        properties: {
          to: { type: 'string', pattern: '^\\+?[1-9]\\d{1,14}$' }, // E.164 format
          body: { type: 'string', maxLength: 1600 }
        },
        additionalProperties: false
      };
      break;
      
    case MessageChannel.PUSH:
      messageSchema = {
        type: 'object',
        required: ['title', 'body', 'deviceToken'],
        properties: {
          title: { type: 'string', maxLength: 255 },
          body: { type: 'string', maxLength: 2000 },
          deviceToken: { type: 'string' },
          data: { type: 'object' }
        },
        additionalProperties: false
      };
      break;
      
    case MessageChannel.WEBHOOK:
      messageSchema = {
        type: 'object',
        required: ['event', 'data'],
        properties: {
          event: { type: 'string' },
          data: { type: 'object' },
          version: { type: 'string' }
        },
        additionalProperties: false
      };
      break;
      
    default:
      return {
        valid: false,
        errors: [{
          field: 'channel',
          message: `Unsupported message channel: ${channel}`,
          code: 'unsupported_channel'
        }]
      };
  }
  
  return validateSchema(messageSchema, payload);
};

/**
 * Sanitizes a string to prevent injection attacks
 * @param input - String to sanitize
 * @returns Sanitized string
 */
export const sanitizeString = (input: string): string => {
  if (!input) return '';
  
  // Replace potentially dangerous characters
  return input
    .replace(/[&<>"']/g, (match) => {
      switch (match) {
        case '&': return '&amp;';
        case '<': return '&lt;';
        case '>': return '&gt;';
        case '"': return '&quot;';
        case "'": return '&#x27;';
        default: return match;
      }
    });
};

/**
 * Sanitizes an object by sanitizing all string properties
 * @param obj - Object to sanitize
 * @returns Sanitized object
 */
export const sanitizeObject = <T extends Record<string, any>>(obj: T): T => {
  if (!obj || typeof obj !== 'object') return obj;
  
  const result = { ...obj };
  
  for (const key in result) {
    if (typeof result[key] === 'string') {
      result[key] = sanitizeString(result[key]);
    } else if (typeof result[key] === 'object' && result[key] !== null) {
      result[key] = sanitizeObject(result[key]);
    }
  }
  
  return result;
};

/**
 * Generates an HMAC-SHA256 signature for a webhook payload
 * @param payload - Payload to sign
 * @param secret - Secret key for signing
 * @returns Signature in hexadecimal format
 */
export const generateWebhookSignature = (payload: string | object, secret: string): string => {
  const data = typeof payload === 'string' ? payload : JSON.stringify(payload);
  
  return crypto
    .createHmac('sha256', secret)
    .update(data)
    .digest('hex');
};

/**
 * Verifies an HMAC-SHA256 signature for a webhook payload
 * @param payload - Payload that was signed
 * @param signature - Signature to verify
 * @param secret - Secret key used for signing
 * @returns True if signature is valid, false otherwise
 */
export const verifyWebhookSignature = (payload: string | object, signature: string, secret: string): boolean => {
  const expectedSignature = generateWebhookSignature(payload, secret);
  
  // Use timing-safe comparison to prevent timing attacks
  try {
    const signatureBuffer = Buffer.from(signature, 'hex');
    const expectedBuffer = Buffer.from(expectedSignature, 'hex');
    
    return signatureBuffer.length === expectedBuffer.length && 
           crypto.timingSafeEqual(signatureBuffer, expectedBuffer);
  } catch (error) {
    return false;
  }
};

/**
 * Creates a webhook signature object with timestamp and signature
 * @param payload - Payload to sign
 * @param secret - Secret key for signing
 * @returns Webhook signature object
 */
export const createWebhookSignature = (payload: string | object, secret: string): IWebhookSignature => {
  const timestamp = Date.now();
  const data = typeof payload === 'string' ? payload : JSON.stringify(payload);
  const stringToSign = `${timestamp}.${data}`;
  
  const signature = crypto
    .createHmac('sha256', secret)
    .update(stringToSign)
    .digest('hex');
  
  return {
    timestamp,
    signature
  };
};

/**
 * Verifies a webhook signature with timestamp
 * @param payload - Payload that was signed
 * @param signatureObj - Signature object with timestamp and signature
 * @param secret - Secret key used for signing
 * @param maxAgeMs - Maximum age of signature in milliseconds (default: 5 minutes)
 * @returns True if signature is valid and not expired, false otherwise
 */
export const verifyWebhookSignatureWithTimestamp = (
  payload: string | object, 
  signatureObj: IWebhookSignature, 
  secret: string,
  maxAgeMs = 5 * 60 * 1000 // 5 minutes
): boolean => {
  const { timestamp, signature } = signatureObj;
  const now = Date.now();
  
  // Check if signature is expired
  if (now - timestamp > maxAgeMs) {
    return false;
  }
  
  const data = typeof payload === 'string' ? payload : JSON.stringify(payload);
  const stringToSign = `${timestamp}.${data}`;
  
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(stringToSign)
    .digest('hex');
  
  // Use timing-safe comparison to prevent timing attacks
  try {
    const signatureBuffer = Buffer.from(signature, 'hex');
    const expectedBuffer = Buffer.from(expectedSignature, 'hex');
    
    return signatureBuffer.length === expectedBuffer.length && 
           crypto.timingSafeEqual(signatureBuffer, expectedBuffer);
  } catch (error) {
    return false;
  }
};

/**
 * Generates a standardized error message for validation failures
 * @param errors - Validation errors
 * @returns Formatted error message
 */
export const formatValidationErrorMessage = (errors: IValidationError[]): string => {
  if (!errors || errors.length === 0) {
    return 'Validation failed';
  }
  
  return errors.map(error => `${error.field}: ${error.message}`).join(', ');
};

/**
 * Throws an error if validation fails
 * @param result - Validation result
 * @param errorMessage - Optional custom error message
 */
export const throwIfInvalid = (result: IValidationResult, errorMessage?: string): void => {
  if (!result.valid && result.errors) {
    const message = errorMessage || formatValidationErrorMessage(result.errors);
    throw new Error(message);
  }
};