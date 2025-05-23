/**
 * @file webhook-service.ts
 * @description Service responsible for formatting, signing, and delivering webhook payloads to configured endpoints.
 * It implements HMAC-SHA256 signatures for payload verification, handles HTTP delivery with proper error handling,
 * and supports delivery confirmation with acknowledgment responses.
 */

import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';
import { v4 as uuidv4 } from 'uuid';
import { createHash, createHmac, timingSafeEqual } from 'crypto';

// Import types
import {
  IWebhookConfig,
  IWebhookPayload,
  IWebhookResponse,
  IWebhookSignature,
  IWebhookDeliveryResult,
  IWebhookDeliveryRequest,
  IWebhookVerificationRequest,
  IWebhookVerificationResult,
  IWebhookHeaders,
  WebhookMethod,
} from '../types/webhook';

// Import configuration
import {
  webhookConfig,
  signatureConfig,
  httpConfig,
  acknowledgmentConfig,
  schemaValidationConfig,
  generateWebhookSignature,
  verifyWebhookSignature,
} from '../config/webhook';

// Import logger
import logger from '../config/logger';

/**
 * WebhookService class responsible for webhook payload delivery and management
 */
export class WebhookService {
  /**
   * Creates a new instance of the WebhookService
   */
  constructor() {
    logger.info('WebhookService initialized');
  }

  /**
   * Generates an HMAC-SHA256 signature for a webhook payload
   * @param payload The webhook payload to sign
   * @param secretKey The secret key to use for signing
   * @returns The signature object containing the signature and timestamp
   */
  public generateSignature(payload: IWebhookPayload, secretKey: string): IWebhookSignature {
    const timestamp = Date.now().toString();
    const payloadString = JSON.stringify(payload);
    
    // Create HMAC using the secret key
    const hmac = createHmac('sha256', secretKey);
    
    // Update HMAC with timestamp and payload
    if (signatureConfig.includeTimestamp) {
      hmac.update(`${timestamp}.${payloadString}`);
    } else {
      hmac.update(payloadString);
    }
    
    // Generate the signature
    const signature = hmac.digest('hex');
    
    logger.debug('Generated webhook signature', { signature, timestamp });
    
    return {
      signature,
      timestamp,
      algorithm: 'HMAC-SHA256',
      encoding: 'hex',
    };
  }

  /**
   * Verifies an HMAC-SHA256 signature for a webhook payload
   * @param payload The webhook payload
   * @param signature The signature to verify
   * @param secretKey The secret key used for signing
   * @param timestamp The timestamp included in the signature
   * @returns Whether the signature is valid
   */
  public verifySignature(
    payload: IWebhookPayload,
    signature: string,
    secretKey: string,
    timestamp?: string
  ): boolean {
    try {
      const payloadString = JSON.stringify(payload);
      
      // Create HMAC using the secret key
      const hmac = createHmac('sha256', secretKey);
      
      // Update HMAC with timestamp and payload if timestamp is provided
      if (timestamp && signatureConfig.includeTimestamp) {
        hmac.update(`${timestamp}.${payloadString}`);
      } else {
        hmac.update(payloadString);
      }
      
      // Generate the expected signature
      const expectedSignature = hmac.digest('hex');
      
      // Use constant-time comparison to prevent timing attacks
      const signatureBuffer = Buffer.from(signature, 'hex');
      const expectedBuffer = Buffer.from(expectedSignature, 'hex');
      
      const isValid = signatureBuffer.length === expectedBuffer.length && 
                      timingSafeEqual(signatureBuffer, expectedBuffer);
      
      logger.debug('Verified webhook signature', { isValid, timestamp });
      
      return isValid;
    } catch (error) {
      logger.error('Error verifying webhook signature', { error });
      return false;
    }
  }

  /**
   * Validates a webhook payload against its schema
   * @param payload The webhook payload to validate
   * @param eventType The event type for schema selection
   * @returns Whether the payload is valid
   */
  public validatePayload(payload: IWebhookPayload, eventType: string): boolean {
    // Skip validation if disabled
    if (!schemaValidationConfig.enabled) {
      return true;
    }
    
    try {
      // In a real implementation, this would use a schema validation library like Joi, Zod, or Ajv
      // For this example, we'll do a simple structure validation
      
      // Check required fields
      if (!payload.id || !payload.timestamp || !payload.eventType || !payload.version || !payload.data) {
        logger.warn('Invalid webhook payload: missing required fields', { eventType });
        return false;
      }
      
      // Check event type matches
      if (payload.eventType !== eventType) {
        logger.warn('Invalid webhook payload: event type mismatch', { 
          expected: eventType, 
          actual: payload.eventType 
        });
        return false;
      }
      
      // Additional validation could be performed here based on the event type
      
      logger.debug('Webhook payload validated successfully', { eventType });
      return true;
    } catch (error) {
      logger.error('Error validating webhook payload', { error, eventType });
      return false;
    }
  }

  /**
   * Creates a webhook payload with the required structure
   * @param eventType The type of event that triggered the webhook
   * @param data The data to include in the payload
   * @param metadata Additional metadata about the event
   * @returns The formatted webhook payload
   */
  public createPayload<T>(
    eventType: string,
    data: T,
    metadata?: Record<string, unknown>
  ): IWebhookPayload<T> {
    const payload: IWebhookPayload<T> = {
      id: uuidv4(),
      timestamp: new Date().toISOString(),
      eventType,
      version: '1.0',
      data,
      metadata,
    };
    
    logger.debug('Created webhook payload', { eventType, id: payload.id });
    return payload;
  }

  /**
   * Prepares headers for a webhook request, including signature headers
   * @param webhook The webhook configuration
   * @param signature The signature information
   * @param additionalHeaders Any additional headers to include
   * @returns The complete set of headers for the request
   */
  private prepareHeaders(
    webhook: IWebhookConfig,
    signature: IWebhookSignature,
    additionalHeaders?: Record<string, string>
  ): IWebhookHeaders {
    // Start with default headers
    const headers: IWebhookHeaders = {
      'Content-Type': 'application/json',
      'User-Agent': `DollarFunding-Webhook-Service/${process.env.npm_package_version || '1.0.0'}`,
      'X-Webhook-ID': webhook.id,
    };
    
    // Add signature headers if enabled
    if (signatureConfig.enabled) {
      headers[signatureConfig.headerName] = signature.signature;
      
      if (signatureConfig.includeTimestamp) {
        headers[signatureConfig.timestampHeaderName] = signature.timestamp;
      }
    }
    
    // Add event type header
    headers['X-Webhook-Event'] = webhook.eventTypes.join(',');
    
    // Add any additional headers
    if (additionalHeaders) {
      Object.entries(additionalHeaders).forEach(([key, value]) => {
        headers[key] = value;
      });
    }
    
    // Add authentication headers if configured
    if (webhook.auth) {
      switch (webhook.auth.type) {
        case 'BASIC':
          if (webhook.auth.username && webhook.auth.password) {
            const auth = Buffer.from(`${webhook.auth.username}:${webhook.auth.password}`).toString('base64');
            headers['Authorization'] = `Basic ${auth}`;
          }
          break;
        case 'BEARER':
          if (webhook.auth.token) {
            headers['Authorization'] = `Bearer ${webhook.auth.token}`;
          }
          break;
        case 'API_KEY':
          if (webhook.auth.apiKeyName && webhook.auth.apiKeyValue) {
            headers[webhook.auth.apiKeyName] = webhook.auth.apiKeyValue;
          }
          break;
        case 'CUSTOM':
          if (webhook.auth.headerName && webhook.auth.headerValue) {
            headers[webhook.auth.headerName] = webhook.auth.headerValue;
          }
          break;
      }
    }
    
    return headers;
  }

  /**
   * Delivers a webhook payload to the configured endpoint
   * @param request The webhook delivery request
   * @returns The delivery result
   */
  public async deliverWebhook(request: IWebhookDeliveryRequest): Promise<IWebhookDeliveryResult> {
    const { webhook, payload, signature, additionalHeaders, timeoutMs, retryAttempt = 0 } = request;
    const startTime = Date.now();
    
    // Create a unique ID for this delivery attempt
    const deliveryId = uuidv4();
    
    // Prepare the delivery result with initial values
    const deliveryResult: IWebhookDeliveryResult = {
      id: deliveryId,
      webhookId: webhook.id,
      eventId: payload.id,
      timestamp: new Date().toISOString(),
      success: false,
      deliveryTimeMs: 0,
      retryCount: retryAttempt,
    };
    
    try {
      // Validate the payload if schema validation is enabled
      if (schemaValidationConfig.enabled && schemaValidationConfig.rejectInvalid) {
        const isValid = this.validatePayload(payload, payload.eventType);
        if (!isValid) {
          throw new Error('Webhook payload validation failed');
        }
      }
      
      // Prepare headers for the request
      const headers = this.prepareHeaders(webhook, signature, additionalHeaders);
      
      // Configure the request
      const requestConfig: AxiosRequestConfig = {
        method: webhook.method,
        url: webhook.url,
        headers,
        data: payload,
        timeout: timeoutMs || httpConfig.timeoutMs,
        maxRedirects: httpConfig.maxRedirects,
        validateStatus: null, // Allow any status code to be handled in our code
      };
      
      // Log the delivery attempt
      logger.info('Delivering webhook', {
        deliveryId,
        webhookId: webhook.id,
        url: webhook.url,
        method: webhook.method,
        eventType: payload.eventType,
        retryAttempt,
      });
      
      // Send the request
      const response = await axios(requestConfig);
      
      // Calculate delivery time
      const endTime = Date.now();
      deliveryResult.deliveryTimeMs = endTime - startTime;
      
      // Record the response details
      deliveryResult.statusCode = response.status;
      deliveryResult.responseBody = JSON.stringify(response.data).substring(0, 1000); // Limit response size
      
      // Determine if the delivery was successful based on status code
      const isSuccessfulStatus = acknowledgmentConfig.successCodes.includes(response.status);
      deliveryResult.success = isSuccessfulStatus;
      
      if (isSuccessfulStatus) {
        logger.info('Webhook delivered successfully', {
          deliveryId,
          webhookId: webhook.id,
          statusCode: response.status,
          deliveryTimeMs: deliveryResult.deliveryTimeMs,
        });
      } else {
        // Delivery failed due to non-success status code
        deliveryResult.errorMessage = `Webhook delivery failed with status code: ${response.status}`;
        
        logger.warn('Webhook delivery failed', {
          deliveryId,
          webhookId: webhook.id,
          statusCode: response.status,
          deliveryTimeMs: deliveryResult.deliveryTimeMs,
          errorMessage: deliveryResult.errorMessage,
        });
      }
      
      return deliveryResult;
    } catch (error) {
      // Calculate delivery time even for errors
      const endTime = Date.now();
      deliveryResult.deliveryTimeMs = endTime - startTime;
      
      // Handle Axios errors
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError;
        
        if (axiosError.response) {
          // The request was made and the server responded with a status code outside of 2xx
          deliveryResult.statusCode = axiosError.response.status;
          deliveryResult.errorMessage = `Webhook delivery failed with status code: ${axiosError.response.status}`;
          deliveryResult.responseBody = JSON.stringify(axiosError.response.data).substring(0, 1000);
        } else if (axiosError.request) {
          // The request was made but no response was received
          deliveryResult.errorMessage = 'Webhook delivery failed: no response received';
        } else {
          // Something happened in setting up the request
          deliveryResult.errorMessage = `Webhook delivery failed: ${axiosError.message}`;
        }
      } else {
        // Handle non-Axios errors
        const err = error as Error;
        deliveryResult.errorMessage = `Webhook delivery failed: ${err.message}`;
      }
      
      logger.error('Error delivering webhook', {
        deliveryId,
        webhookId: webhook.id,
        url: webhook.url,
        method: webhook.method,
        eventType: payload.eventType,
        retryAttempt,
        error: deliveryResult.errorMessage,
        deliveryTimeMs: deliveryResult.deliveryTimeMs,
      });
      
      return deliveryResult;
    }
  }

  /**
   * Verifies that a webhook endpoint is valid and accessible
   * @param request The webhook verification request
   * @returns The verification result
   */
  public async verifyWebhookEndpoint(request: IWebhookVerificationRequest): Promise<IWebhookVerificationResult> {
    const { url, method, headers, auth, timeoutMs } = request;
    const startTime = Date.now();
    
    // Prepare the verification result with initial values
    const verificationResult: IWebhookVerificationResult = {
      success: false,
    };
    
    try {
      // Prepare a test payload
      const testPayload = {
        id: uuidv4(),
        timestamp: new Date().toISOString(),
        eventType: 'webhook.verification',
        version: '1.0',
        data: {
          message: 'This is a test webhook to verify endpoint configuration.',
        },
      };
      
      // Configure the request
      const requestConfig: AxiosRequestConfig = {
        method: method || WebhookMethod.POST,
        url,
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': `DollarFunding-Webhook-Service/${process.env.npm_package_version || '1.0.0'}`,
          'X-Webhook-Verification': 'true',
          ...headers,
        },
        data: testPayload,
        timeout: timeoutMs || httpConfig.timeoutMs,
        validateStatus: null, // Allow any status code to be handled in our code
      };
      
      // Add authentication if provided
      if (auth) {
        switch (auth.type) {
          case 'BASIC':
            if (auth.username && auth.password) {
              requestConfig.auth = {
                username: auth.username,
                password: auth.password,
              };
            }
            break;
          case 'BEARER':
            if (auth.token) {
              requestConfig.headers = {
                ...requestConfig.headers,
                'Authorization': `Bearer ${auth.token}`,
              };
            }
            break;
          case 'API_KEY':
            if (auth.apiKeyName && auth.apiKeyValue) {
              requestConfig.headers = {
                ...requestConfig.headers,
                [auth.apiKeyName]: auth.apiKeyValue,
              };
            }
            break;
          case 'CUSTOM':
            if (auth.headerName && auth.headerValue) {
              requestConfig.headers = {
                ...requestConfig.headers,
                [auth.headerName]: auth.headerValue,
              };
            }
            break;
        }
      }
      
      // Log the verification attempt
      logger.info('Verifying webhook endpoint', { url, method });
      
      // Send the request
      const response = await axios(requestConfig);
      
      // Calculate response time
      const endTime = Date.now();
      verificationResult.responseTimeMs = endTime - startTime;
      
      // Record the response details
      verificationResult.statusCode = response.status;
      
      // Determine if the verification was successful based on status code
      // For verification, we consider any 2xx or 3xx status code as successful
      const isSuccessfulStatus = response.status >= 200 && response.status < 400;
      verificationResult.success = isSuccessfulStatus;
      
      if (isSuccessfulStatus) {
        logger.info('Webhook endpoint verified successfully', {
          url,
          statusCode: response.status,
          responseTimeMs: verificationResult.responseTimeMs,
        });
      } else {
        // Verification failed due to non-success status code
        verificationResult.errorMessage = `Webhook verification failed with status code: ${response.status}`;
        
        logger.warn('Webhook endpoint verification failed', {
          url,
          statusCode: response.status,
          responseTimeMs: verificationResult.responseTimeMs,
          errorMessage: verificationResult.errorMessage,
        });
      }
      
      return verificationResult;
    } catch (error) {
      // Calculate response time even for errors
      const endTime = Date.now();
      verificationResult.responseTimeMs = endTime - startTime;
      
      // Handle Axios errors
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError;
        
        if (axiosError.response) {
          // The request was made and the server responded with a status code outside of 2xx
          verificationResult.statusCode = axiosError.response.status;
          verificationResult.errorMessage = `Webhook verification failed with status code: ${axiosError.response.status}`;
          verificationResult.errorDetails = { data: axiosError.response.data };
        } else if (axiosError.request) {
          // The request was made but no response was received
          verificationResult.errorMessage = 'Webhook verification failed: no response received';
          verificationResult.errorDetails = { request: 'Request sent but no response received' };
        } else {
          // Something happened in setting up the request
          verificationResult.errorMessage = `Webhook verification failed: ${axiosError.message}`;
          verificationResult.errorDetails = { message: axiosError.message };
        }
      } else {
        // Handle non-Axios errors
        const err = error as Error;
        verificationResult.errorMessage = `Webhook verification failed: ${err.message}`;
        verificationResult.errorDetails = { message: err.message };
      }
      
      logger.error('Error verifying webhook endpoint', {
        url,
        method,
        error: verificationResult.errorMessage,
        responseTimeMs: verificationResult.responseTimeMs,
      });
      
      return verificationResult;
    }
  }

  /**
   * Processes a webhook delivery result and determines if a retry is needed
   * @param deliveryResult The result of a webhook delivery attempt
   * @param webhook The webhook configuration
   * @returns Whether a retry should be attempted
   */
  public shouldRetryDelivery(deliveryResult: IWebhookDeliveryResult, webhook: IWebhookConfig): boolean {
    // Don't retry if already successful
    if (deliveryResult.success) {
      return false;
    }
    
    // Don't retry if max retries reached
    if (deliveryResult.retryCount >= webhook.retryPolicy.maxRetries) {
      logger.info('Max retry attempts reached for webhook', {
        deliveryId: deliveryResult.id,
        webhookId: webhook.id,
        maxRetries: webhook.retryPolicy.maxRetries,
        retryCount: deliveryResult.retryCount,
      });
      return false;
    }
    
    // Check if status code is retryable
    if (deliveryResult.statusCode) {
      const isRetryableStatusCode = webhook.retryPolicy.retryableStatusCodes.includes(deliveryResult.statusCode);
      
      if (!isRetryableStatusCode) {
        // Check if it's a 5xx error, which is typically retryable
        const isServerError = deliveryResult.statusCode >= 500 && deliveryResult.statusCode < 600;
        
        if (!isServerError) {
          logger.info('Non-retryable status code for webhook', {
            deliveryId: deliveryResult.id,
            webhookId: webhook.id,
            statusCode: deliveryResult.statusCode,
          });
          return false;
        }
      }
    }
    
    // If we got here, we should retry
    logger.info('Scheduling webhook delivery for retry', {
      deliveryId: deliveryResult.id,
      webhookId: webhook.id,
      retryCount: deliveryResult.retryCount,
      nextRetryAttempt: deliveryResult.retryCount + 1,
    });
    
    return true;
  }

  /**
   * Calculates the next retry time for a failed webhook delivery
   * @param retryAttempt The current retry attempt (0-based)
   * @param retryPolicy The retry policy to use
   * @returns The timestamp for the next retry attempt
   */
  public calculateNextRetryTime(retryAttempt: number, retryPolicy: IWebhookRetryPolicy): Date {
    // Calculate the base delay using exponential backoff
    const baseDelayMs = Math.min(
      retryPolicy.initialDelayMs * Math.pow(retryPolicy.backoffFactor, retryAttempt),
      retryPolicy.maxDelayMs
    );
    
    // Add jitter if enabled to prevent thundering herd problem
    let delayMs = baseDelayMs;
    if (retryPolicy.useJitter) {
      const jitterAmount = baseDelayMs * 0.1; // 10% jitter
      delayMs = baseDelayMs + (Math.random() * jitterAmount * 2) - jitterAmount;
    }
    
    // Calculate the next retry time
    const nextRetryTime = new Date(Date.now() + delayMs);
    
    logger.debug('Calculated next retry time', {
      retryAttempt,
      baseDelayMs,
      actualDelayMs: delayMs,
      nextRetryTime: nextRetryTime.toISOString(),
    });
    
    return nextRetryTime;
  }
}

// Export a singleton instance of the WebhookService
export default new WebhookService();