/**
 * Validation Middleware
 * 
 * This middleware validates request bodies, parameters, and queries against JSON schemas,
 * ensuring that all incoming data meets the expected format and constraints.
 * It prevents invalid data from entering the system and provides clear error messages
 * for validation failures.
 */

import { Request, Response, NextFunction } from 'express';
import { z, ZodError, ZodSchema } from 'zod';
import { getErrorMessage } from '../utils/error-message';

/**
 * Error response structure for validation errors
 */
export interface ValidationErrorResponse {
  status: 'error';
  message: string;
  errors: {
    path: string;
    message: string;
  }[];
}

/**
 * Options for the validation middleware
 */
export interface ValidationOptions {
  /** When true, will strip additional properties not defined in the schema */
  stripUnknown?: boolean;
  /** Custom error message to use instead of the default */
  errorMessage?: string;
  /** Status code to use for validation errors (defaults to 400) */
  errorStatusCode?: number;
}

/**
 * Default validation options
 */
const defaultOptions: ValidationOptions = {
  stripUnknown: false,
  errorStatusCode: 400,
};

/**
 * Formats a ZodError into a standardized validation error response
 * 
 * @param error The ZodError to format
 * @returns A structured validation error response
 */
const formatZodError = (error: ZodError): ValidationErrorResponse => {
  return {
    status: 'error',
    message: 'Validation failed',
    errors: error.errors.map((err) => ({
      path: err.path.join('.'),
      message: err.message,
    })),
  };
};

/**
 * Creates a middleware function that validates the request body against a schema
 * 
 * @param schema The Zod schema to validate against
 * @param options Validation options
 * @returns Express middleware function
 */
export const validateBody = <T extends ZodSchema>(
  schema: T,
  options: ValidationOptions = defaultOptions
) => {
  const opts = { ...defaultOptions, ...options };

  return (req: Request, res: Response, next: NextFunction) => {
    try {
      const parseOptions = opts.stripUnknown ? { stripUnknown: true } : {};
      req.body = schema.parse(req.body, parseOptions);
      next();
    } catch (error) {
      if (error instanceof ZodError) {
        const formattedError = formatZodError(error);
        return res.status(opts.errorStatusCode || 400).json({
          ...formattedError,
          message: opts.errorMessage || formattedError.message,
        });
      }
      
      return res.status(opts.errorStatusCode || 400).json({
        status: 'error',
        message: opts.errorMessage || getErrorMessage(error) || 'Validation failed',
        errors: [],
      });
    }
  };
};

/**
 * Creates a middleware function that validates URL parameters against a schema
 * 
 * @param schema The Zod schema to validate against
 * @param options Validation options
 * @returns Express middleware function
 */
export const validateParams = <T extends ZodSchema>(
  schema: T,
  options: ValidationOptions = defaultOptions
) => {
  const opts = { ...defaultOptions, ...options };

  return (req: Request, res: Response, next: NextFunction) => {
    try {
      const parseOptions = opts.stripUnknown ? { stripUnknown: true } : {};
      req.params = schema.parse(req.params, parseOptions);
      next();
    } catch (error) {
      if (error instanceof ZodError) {
        const formattedError = formatZodError(error);
        return res.status(opts.errorStatusCode || 400).json({
          ...formattedError,
          message: opts.errorMessage || formattedError.message,
        });
      }
      
      return res.status(opts.errorStatusCode || 400).json({
        status: 'error',
        message: opts.errorMessage || getErrorMessage(error) || 'Parameter validation failed',
        errors: [],
      });
    }
  };
};

/**
 * Creates a middleware function that validates query parameters against a schema
 * 
 * @param schema The Zod schema to validate against
 * @param options Validation options
 * @returns Express middleware function
 */
export const validateQuery = <T extends ZodSchema>(
  schema: T,
  options: ValidationOptions = defaultOptions
) => {
  const opts = { ...defaultOptions, ...options };

  return (req: Request, res: Response, next: NextFunction) => {
    try {
      const parseOptions = opts.stripUnknown ? { stripUnknown: true } : {};
      req.query = schema.parse(req.query, parseOptions) as any;
      next();
    } catch (error) {
      if (error instanceof ZodError) {
        const formattedError = formatZodError(error);
        return res.status(opts.errorStatusCode || 400).json({
          ...formattedError,
          message: opts.errorMessage || formattedError.message,
        });
      }
      
      return res.status(opts.errorStatusCode || 400).json({
        status: 'error',
        message: opts.errorMessage || getErrorMessage(error) || 'Query validation failed',
        errors: [],
      });
    }
  };
};

/**
 * Creates a middleware function that validates the entire request (body, params, query) against schemas
 * 
 * @param schemas Object containing schemas for body, params, and/or query
 * @param options Validation options
 * @returns Express middleware function
 */
export const validateRequest = (
  schemas: {
    body?: ZodSchema;
    params?: ZodSchema;
    query?: ZodSchema;
  },
  options: ValidationOptions = defaultOptions
) => {
  const opts = { ...defaultOptions, ...options };

  return (req: Request, res: Response, next: NextFunction) => {
    try {
      const parseOptions = opts.stripUnknown ? { stripUnknown: true } : {};
      
      // Validate body if schema provided
      if (schemas.body) {
        req.body = schemas.body.parse(req.body, parseOptions);
      }
      
      // Validate params if schema provided
      if (schemas.params) {
        req.params = schemas.params.parse(req.params, parseOptions);
      }
      
      // Validate query if schema provided
      if (schemas.query) {
        req.query = schemas.query.parse(req.query, parseOptions) as any;
      }
      
      next();
    } catch (error) {
      if (error instanceof ZodError) {
        const formattedError = formatZodError(error);
        return res.status(opts.errorStatusCode || 400).json({
          ...formattedError,
          message: opts.errorMessage || formattedError.message,
        });
      }
      
      return res.status(opts.errorStatusCode || 400).json({
        status: 'error',
        message: opts.errorMessage || getErrorMessage(error) || 'Request validation failed',
        errors: [],
      });
    }
  };
};

/**
 * Creates a middleware function that applies a custom validation function to the request
 * 
 * @param validator Custom validation function that throws an error if validation fails
 * @param options Validation options
 * @returns Express middleware function
 */
export const validateCustom = (
  validator: (req: Request) => void | Promise<void>,
  options: ValidationOptions = defaultOptions
) => {
  const opts = { ...defaultOptions, ...options };

  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      await validator(req);
      next();
    } catch (error) {
      if (error instanceof ZodError) {
        const formattedError = formatZodError(error);
        return res.status(opts.errorStatusCode || 400).json({
          ...formattedError,
          message: opts.errorMessage || formattedError.message,
        });
      }
      
      return res.status(opts.errorStatusCode || 400).json({
        status: 'error',
        message: opts.errorMessage || getErrorMessage(error) || 'Custom validation failed',
        errors: [],
      });
    }
  };
};

/**
 * Creates a middleware function that sanitizes and validates webhook payloads
 * 
 * @param schema The Zod schema to validate against
 * @param options Validation options
 * @returns Express middleware function
 */
export const validateWebhookPayload = <T extends ZodSchema>(
  schema: T,
  options: ValidationOptions = defaultOptions
) => {
  const opts = { ...defaultOptions, ...options };

  return (req: Request, res: Response, next: NextFunction) => {
    try {
      // Apply additional security checks for webhook payloads
      if (!req.body || typeof req.body !== 'object') {
        throw new Error('Invalid webhook payload format');
      }

      // Sanitize the payload to prevent injection attacks
      const sanitizedPayload = sanitizePayload(req.body);
      
      // Validate the sanitized payload against the schema
      const parseOptions = opts.stripUnknown ? { stripUnknown: true } : {};
      req.body = schema.parse(sanitizedPayload, parseOptions);
      next();
    } catch (error) {
      if (error instanceof ZodError) {
        const formattedError = formatZodError(error);
        return res.status(opts.errorStatusCode || 400).json({
          ...formattedError,
          message: opts.errorMessage || formattedError.message,
        });
      }
      
      return res.status(opts.errorStatusCode || 400).json({
        status: 'error',
        message: opts.errorMessage || getErrorMessage(error) || 'Webhook payload validation failed',
        errors: [],
      });
    }
  };
};

/**
 * Sanitizes a payload object to prevent injection attacks
 * 
 * @param payload The payload to sanitize
 * @returns Sanitized payload
 */
const sanitizePayload = (payload: Record<string, any>): Record<string, any> => {
  // Create a new object to avoid modifying the original
  const sanitized: Record<string, any> = {};
  
  // Process each property in the payload
  for (const [key, value] of Object.entries(payload)) {
    // Handle nested objects recursively
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      sanitized[key] = sanitizePayload(value);
    }
    // Handle arrays by mapping each element
    else if (Array.isArray(value)) {
      sanitized[key] = value.map(item => {
        if (item && typeof item === 'object') {
          return sanitizePayload(item);
        }
        return sanitizeString(item);
      });
    }
    // Handle string values
    else if (typeof value === 'string') {
      sanitized[key] = sanitizeString(value);
    }
    // Pass through other primitive values
    else {
      sanitized[key] = value;
    }
  }
  
  return sanitized;
};

/**
 * Sanitizes a string to prevent XSS and injection attacks
 * 
 * @param input The string to sanitize
 * @returns Sanitized string
 */
const sanitizeString = (input: any): string => {
  if (typeof input !== 'string') {
    return input;
  }
  
  // Basic sanitization to prevent script injection
  return input
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
};

// Export all validation middleware functions
export default {
  validateBody,
  validateParams,
  validateQuery,
  validateRequest,
  validateCustom,
  validateWebhookPayload,
};