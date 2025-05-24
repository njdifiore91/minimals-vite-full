/**
 * Validation Utilities
 * 
 * This file provides validation utilities for webhook configurations, notification payloads,
 * and message formats. It implements schema validation, format checking, and data sanitization
 * to ensure consistent and secure data handling throughout the Notification Service.
 * 
 * Key features:
 * - JSON Schema validation for webhook payloads
 * - Webhook configuration validation (URL, method, headers)
 * - Format validation for notification messages
 * - Data sanitization to prevent injection attacks
 * - Consistent error message generation
 */

import Ajv, { ErrorObject, ValidateFunction } from 'ajv';
import addFormats from 'ajv-formats';
import { IWebhookConfig, IWebhookPayload, WebhookMethod, IWebhookEventType } from '../types/webhook';
import { IErrorResponse, ILogContext } from '../types/common';
import { NotificationType, NotificationStatus, INotificationPayload } from '../types/notification';

// Initialize Ajv instance with options
const ajv = new Ajv({
  allErrors: true,         // Return all errors, not just the first one
  removeAdditional: 'all', // Remove additional properties not in schema
  useDefaults: true,       // Apply default values from schema
  coerceTypes: true,       // Convert data types when possible
  strict: false            // Allow keywords not defined in the JSON Schema specification
});

// Add formats for validation (email, date-time, uri, etc.)
addFormats(ajv);

// Add custom formats
ajv.addFormat('event-type', {
  type: 'string',
  validate: (eventType: string) => isValidEventType(eventType)
});

// Register schemas for reuse
const WEBHOOK_PAYLOAD_SCHEMA = {
  type: 'object',
  required: ['id', 'event', 'timestamp', 'version', 'environment', 'data'],
  properties: {
    id: { type: 'string', format: 'uuid' },
    event: { type: 'string', format: 'event-type' },
    timestamp: { type: 'string', format: 'date-time' },
    version: { type: 'string', pattern: '^\\d+\\.\\d+(\\.\\d+)?$' },
    environment: { type: 'string', enum: ['development', 'staging', 'production'] },
    data: { type: 'object' },
    metadata: { 
      type: 'object',
      properties: {
        applicationId: { type: 'string' },
        merchantId: { type: 'string' },
        documentIds: { type: 'array', items: { type: 'string' } }
      }
    }
  },
  additionalProperties: false
};

const NOTIFICATION_PAYLOAD_SCHEMA = {
  type: 'object',
  required: ['id', 'type', 'status', 'content', 'createdAt'],
  properties: {
    id: { type: 'string', format: 'uuid' },
    type: { type: 'string', enum: Object.values(NotificationType) },
    status: { type: 'string', enum: Object.values(NotificationStatus) },
    content: { type: 'object' },
    recipients: { 
      type: 'array', 
      items: {
        type: 'object',
        required: ['type', 'value'],
        properties: {
          type: { type: 'string', enum: ['email', 'webhook', 'sms', 'push'] },
          value: { type: 'string' }
        }
      }
    },
    createdAt: { type: 'string', format: 'date-time' },
    updatedAt: { type: 'string', format: 'date-time' },
    metadata: { type: 'object' }
  },
  additionalProperties: false
};

// Register schemas with Ajv
ajv.addSchema(WEBHOOK_PAYLOAD_SCHEMA, 'webhook-payload');
ajv.addSchema(NOTIFICATION_PAYLOAD_SCHEMA, 'notification-payload');

/**
 * Interface for validation result
 */
export interface IValidationResult {
  valid: boolean;
  errors: ErrorObject[] | null;
  errorMessage?: string;
}

/**
 * Validates data against a JSON schema
 * @param schema - JSON schema to validate against
 * @param data - Data to validate
 * @returns Validation result
 */
export function validateAgainstSchema(schema: object, data: unknown): IValidationResult {
  try {
    // Compile schema if not already compiled
    let validate: ValidateFunction;
    if (typeof schema === 'function') {
      validate = schema as ValidateFunction;
    } else {
      validate = ajv.compile(schema);
    }

    // Validate data against schema
    const valid = validate(data);
    
    return {
      valid,
      errors: validate.errors,
      errorMessage: valid ? undefined : formatValidationErrors(validate.errors)
    };
  } catch (error) {
    return {
      valid: false,
      errors: null,
      errorMessage: `Schema validation error: ${(error as Error).message}`
    };
  }
}

/**
 * Formats validation errors into a readable string
 * @param errors - Validation errors
 * @returns Formatted error message
 */
export function formatValidationErrors(errors: ErrorObject[] | null | undefined): string {
  if (!errors || errors.length === 0) {
    return 'Unknown validation error';
  }

  return errors.map(error => {
    const path = error.instancePath || '';
    const property = error.params.missingProperty ? 
      `/${error.params.missingProperty}` : 
      '';
    
    return `${path}${property} ${error.message}`;
  }).join('; ');
}

/**
 * Creates a standard error response for validation errors
 * @param errors - Validation errors
 * @param correlationId - Request correlation ID
 * @returns Standardized error response
 */
export function createValidationErrorResponse(
  errors: ErrorObject[] | null | undefined,
  correlationId: string
): IErrorResponse {
  return {
    statusCode: 400,
    message: 'Validation error',
    errorCode: 'VALIDATION_ERROR',
    correlationId,
    timestamp: new Date().toISOString(),
    details: {
      errors: errors ? errors.map(e => ({
        path: e.instancePath,
        message: e.message,
        params: e.params
      })) : []
    }
  };
}

/**
 * Validates a webhook configuration
 * @param config - Webhook configuration to validate
 * @returns Validation result
 */
export function validateWebhookConfig(config: IWebhookConfig): IValidationResult {
  const errors: string[] = [];

  // Validate URL
  if (!isValidUrl(config.url)) {
    errors.push('Invalid webhook URL');
  }

  // Validate HTTP method
  if (!Object.values(WebhookMethod).includes(config.method)) {
    errors.push(`Invalid HTTP method: ${config.method}`);
  }

  // Validate timeout
  if (typeof config.timeoutMs !== 'number' || config.timeoutMs < 100 || config.timeoutMs > 30000) {
    errors.push('Timeout must be between 100ms and 30000ms');
  }

  // Validate retry policy
  if (config.retryPolicy) {
    if (config.retryPolicy.maxRetries < 0 || config.retryPolicy.maxRetries > 10) {
      errors.push('Maximum retries must be between 0 and 10');
    }

    if (config.retryPolicy.initialDelayMs < 100 || config.retryPolicy.initialDelayMs > 60000) {
      errors.push('Initial delay must be between 100ms and 60000ms');
    }

    if (config.retryPolicy.maxDelayMs < config.retryPolicy.initialDelayMs || config.retryPolicy.maxDelayMs > 3600000) {
      errors.push('Maximum delay must be between initial delay and 3600000ms (1 hour)');
    }
  }

  return {
    valid: errors.length === 0,
    errors: errors.length > 0 ? errors.map(msg => ({ message: msg } as ErrorObject)) : null,
    errorMessage: errors.length > 0 ? errors.join('; ') : undefined
  };
}

/**
 * Validates a webhook payload
 * @param payload - Webhook payload to validate
 * @returns Validation result
 */
export function validateWebhookPayload(payload: IWebhookPayload): IValidationResult {
  // Use the pre-registered schema
  return validateAgainstSchema(ajv.getSchema('webhook-payload') || WEBHOOK_PAYLOAD_SCHEMA, payload);
}

/**
 * Validates a notification payload
 * @param payload - Notification payload to validate
 * @returns Validation result
 */
export function validateNotificationPayload(payload: INotificationPayload): IValidationResult {
  // Use the pre-registered schema
  return validateAgainstSchema(ajv.getSchema('notification-payload') || NOTIFICATION_PAYLOAD_SCHEMA, payload);
}

/**
 * Validates a URL string
 * @param url - URL to validate
 * @returns Whether the URL is valid
 */
export function isValidUrl(url: string): boolean {
  try {
    const urlObj = new URL(url);
    return urlObj.protocol === 'http:' || urlObj.protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * Sanitizes a string to prevent injection attacks
 * @param input - String to sanitize
 * @returns Sanitized string
 */
export function sanitizeString(input: string): string {
  if (typeof input !== 'string') {
    return '';
  }
  
  // Remove potentially dangerous characters
  return input
    .replace(/[\u0000-\u001F\u007F-\u009F]/g, '') // Control characters
    .replace(/[\u2028\u2029]/g, '') // Line/paragraph separators
    .replace(/[\<\>\&\"\'\`]/g, match => { // HTML special chars
      switch (match) {
        case '<': return '&lt;';
        case '>': return '&gt;';
        case '&': return '&amp;';
        case '"': return '&quot;';
        case '\'': return '&#x27;';
        case '`': return '&#x60;';
        default: return match;
      }
    })
    // Additional sanitization for script tags and other potentially harmful patterns
    .replace(/javascript\s*:/gi, '')
    .replace(/data\s*:/gi, '')
    .replace(/vbscript\s*:/gi, '')
    .replace(/on\w+\s*=/gi, '');
}

/**
 * Sanitizes an object by sanitizing all string properties
 * @param obj - Object to sanitize
 * @returns Sanitized object
 */
export function sanitizeObject<T extends Record<string, any>>(obj: T): T {
  if (!obj || typeof obj !== 'object') {
    return obj;
  }

  const result = { ...obj };

  for (const key in result) {
    if (Object.prototype.hasOwnProperty.call(result, key)) {
      const value = result[key];
      
      if (typeof value === 'string') {
        result[key] = sanitizeString(value);
      } else if (value && typeof value === 'object' && !Array.isArray(value)) {
        result[key] = sanitizeObject(value);
      } else if (Array.isArray(value)) {
        result[key] = value.map(item => {
          if (typeof item === 'string') {
            return sanitizeString(item);
          } else if (item && typeof item === 'object') {
            return sanitizeObject(item);
          }
          return item;
        });
      }
    }
  }

  return result;
}

/**
 * Sanitizes and validates webhook headers
 * @param headers - Headers to sanitize and validate
 * @returns Sanitized and validated headers
 */
export function sanitizeAndValidateHeaders(headers: Record<string, string>): Record<string, string> {
  const sanitizedHeaders: Record<string, string> = {};
  
  // Sanitize header names and values
  for (const [key, value] of Object.entries(headers)) {
    // Sanitize header name (only allow alphanumeric, dash, and underscore)
    const sanitizedKey = key.replace(/[^a-zA-Z0-9-_]/g, '');
    
    // Skip empty header names
    if (!sanitizedKey) continue;
    
    // Sanitize header value
    sanitizedHeaders[sanitizedKey] = sanitizeString(value);
  }
  
  return sanitizedHeaders;
}

/**
 * Validates a webhook event type
 * @param eventType - Event type to validate
 * @returns Whether the event type is valid
 */
export function isValidEventType(eventType: string): boolean {
  if (typeof eventType !== 'string' || eventType.trim() === '') {
    return false;
  }
  
  // Event types should follow a specific pattern (e.g., 'application.status.updated')
  // Format: domain.entity.action
  const eventTypePattern = /^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*){1,2}$/;
  return eventTypePattern.test(eventType);
}

/**
 * Validates a webhook event type against registered event types
 * @param eventType - Event type to validate
 * @param registeredEventTypes - List of registered event types
 * @returns Whether the event type is valid and registered
 */
export function isRegisteredEventType(eventType: string, registeredEventTypes: IWebhookEventType[]): boolean {
  if (!isValidEventType(eventType)) {
    return false;
  }
  
  return registeredEventTypes.some(et => et.id === eventType && et.enabled);
}

/**
 * Validates an email address
 * @param email - Email address to validate
 * @returns Whether the email address is valid
 */
export function isValidEmail(email: string): boolean {
  // Basic email validation regex
  const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return emailPattern.test(email);
}

/**
 * Validates a phone number
 * @param phone - Phone number to validate
 * @returns Whether the phone number is valid
 */
export function isValidPhoneNumber(phone: string): boolean {
  // Basic international phone number validation (E.123 format)
  const phonePattern = /^\+?[1-9]\d{1,14}$/;
  return phonePattern.test(phone);
}

/**
 * Validates a UUID
 * @param uuid - UUID to validate
 * @returns Whether the UUID is valid
 */
export function isValidUuid(uuid: string): boolean {
  const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidPattern.test(uuid);
}

/**
 * Sanitizes a SQL-like query string to prevent SQL injection
 * @param query - Query string to sanitize
 * @returns Sanitized query string
 */
export function sanitizeSqlLikeQuery(query: string): string {
  if (typeof query !== 'string') {
    return '';
  }
  
  // Escape special characters used in SQL injection attacks
  return query
    .replace(/[\\\"\'\;\-\-\=\(\)\*\&\^\%\$\#\@\!\~\`]/g, '') // Remove SQL special chars
    .replace(/\s+/g, ' ') // Normalize whitespace
    .trim();
}

/**
 * Validates and sanitizes a search query
 * @param query - Search query to validate and sanitize
 * @returns Sanitized search query
 */
export function validateAndSanitizeSearchQuery(query: string): string {
  if (typeof query !== 'string') {
    return '';
  }
  
  // Limit length
  let sanitized = query.slice(0, 100);
  
  // Remove potentially dangerous characters
  sanitized = sanitizeString(sanitized);
  
  // Remove SQL-like injection patterns
  sanitized = sanitizeSqlLikeQuery(sanitized);
  
  return sanitized;
}

/**
 * Validates a webhook configuration against security requirements
 * @param config - Webhook configuration to validate
 * @returns Validation result with security-specific checks
 */
export function validateWebhookSecurity(config: IWebhookConfig): IValidationResult {
  const errors: string[] = [];

  // Validate HTTPS for production environment
  if (process.env.NODE_ENV === 'production' && !config.url.startsWith('https://')) {
    errors.push('HTTPS is required for webhook URLs in production environment');
  }

  // Validate secret length and complexity
  if (!config.secret || config.secret.length < 32) {
    errors.push('Webhook secret must be at least 32 characters long');
  }

  // Check for complex secret with mixed character types
  const hasUppercase = /[A-Z]/.test(config.secret);
  const hasLowercase = /[a-z]/.test(config.secret);
  const hasNumbers = /[0-9]/.test(config.secret);
  const hasSpecialChars = /[^A-Za-z0-9]/.test(config.secret);
  
  if (!(hasUppercase && hasLowercase && hasNumbers && hasSpecialChars)) {
    errors.push('Webhook secret must contain uppercase, lowercase, numbers, and special characters');
  }

  // Validate SSL verification setting
  if (process.env.NODE_ENV === 'production' && config.verifySSL === false) {
    errors.push('SSL verification cannot be disabled in production environment');
  }

  return {
    valid: errors.length === 0,
    errors: errors.length > 0 ? errors.map(msg => ({ message: msg } as ErrorObject)) : null,
    errorMessage: errors.length > 0 ? errors.join('; ') : undefined
  };
}

/**
 * Validates a log context object
 * @param context - Log context to validate
 * @returns Validation result
 */
export function validateLogContext(context: ILogContext): IValidationResult {
  const errors: string[] = [];

  if (!context.correlationId) {
    errors.push('Correlation ID is required');
  }

  if (!context.serviceName) {
    errors.push('Service name is required');
  }

  if (!context.timestamp) {
    errors.push('Timestamp is required');
  }

  return {
    valid: errors.length === 0,
    errors: errors.length > 0 ? errors.map(msg => ({ message: msg } as ErrorObject)) : null,
    errorMessage: errors.length > 0 ? errors.join('; ') : undefined
  };
}