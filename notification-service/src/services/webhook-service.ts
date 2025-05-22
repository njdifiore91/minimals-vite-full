/**
 * Webhook Service
 * 
 * This service is responsible for formatting, signing, and delivering webhook payloads to configured endpoints.
 * It implements HMAC-SHA256 signatures for payload verification, handles HTTP delivery with proper error handling,
 * and supports delivery confirmation with acknowledgment responses.
 */

import axios, { AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import crypto from 'crypto';
import { v4 as uuidv4 } from 'uuid';
import { Logger } from 'winston';

import { config } from '../config';
import {
  IWebhookConfig,
  IWebhookPayload,
  IWebhookHeaders,
  IWebhookSignature,
  IWebhookResponse,
  IWebhookDeliveryResult,
  WebhookMethod,
  WebhookStatus,
} from '../types/webhook';

/**
 * WebhookService class responsible for webhook payload formatting, signing, and delivery
 */
export class WebhookService {
  private logger: Logger;
  private readonly signatureHeaderName: string = 'X-Webhook-Signature';
  private readonly timestampHeaderName: string = 'X-Webhook-Timestamp';
  private readonly idHeaderName: string = 'X-Webhook-ID';
  private readonly eventHeaderName: string = 'X-Webhook-Event';
  private readonly userAgent: string = 'DollarFunding-Webhook-Service/1.0';
  
  /**
   * Creates a new instance of WebhookService
   * @param logger Winston logger instance for logging
   */
  constructor(logger: Logger) {
    this.logger = logger;
  }

  /**
   * Generates an HMAC-SHA256 signature for a webhook payload
   * @param payload The webhook payload to sign
   * @param secret The customer-specific secret key
   * @param timestamp The timestamp to include in the signature
   * @returns The signature object containing the generated signature
   */
  public generateSignature(payload: IWebhookPayload, secret: string, timestamp: string): IWebhookSignature {
    try {
      // Convert payload to string if it's not already
      const payloadString = typeof payload === 'string' ? payload : JSON.stringify(payload);
      
      // Create HMAC using SHA256 algorithm and the customer's secret key
      const hmac = crypto.createHmac('sha256', secret);
      
      // Update HMAC with timestamp and payload
      hmac.update(`${timestamp}.${payloadString}`);
      
      // Generate the signature in hex format
      const signature = hmac.digest('hex');
      
      return {
        algorithm: 'sha256',
        secret,
        signature,
        timestamp,
        payload: payloadString,
        headerName: this.signatureHeaderName,
        signatureFormat: 't={timestamp},v1={signature}'
      };
    } catch (error) {
      this.logger.error('Error generating webhook signature', {
        error: (error as Error).message,
        payload: typeof payload === 'object' ? JSON.stringify(payload) : payload,
        timestamp
      });
      throw new Error(`Failed to generate webhook signature: ${(error as Error).message}`);
    }
  }

  /**
   * Validates a webhook payload against its schema
   * @param payload The webhook payload to validate
   * @param eventType The type of event for schema selection
   * @returns True if the payload is valid, false otherwise
   */
  public validatePayload(payload: IWebhookPayload, eventType: string): boolean {
    try {
      // Basic validation checks
      if (!payload) {
        this.logger.warn('Empty webhook payload', { eventType });
        return false;
      }

      if (!payload.id || !payload.event || !payload.timestamp || !payload.version) {
        this.logger.warn('Webhook payload missing required fields', { 
          eventType,
          payload: JSON.stringify(payload)
        });
        return false;
      }

      // TODO: Implement schema validation using a library like Joi or Zod
      // This would validate the payload structure against a predefined schema for the event type
      
      return true;
    } catch (error) {
      this.logger.error('Error validating webhook payload', {
        error: (error as Error).message,
        eventType,
        payload: JSON.stringify(payload)
      });
      return false;
    }
  }

  /**
   * Prepares HTTP headers for a webhook request
   * @param webhookConfig The webhook configuration
   * @param signature The signature object
   * @param payload The webhook payload
   * @returns The prepared HTTP headers
   */
  private prepareHeaders(webhookConfig: IWebhookConfig, signature: IWebhookSignature, payload: IWebhookPayload): IWebhookHeaders {
    const headers: IWebhookHeaders = {
      'Content-Type': webhookConfig.contentType || 'application/json',
      'User-Agent': this.userAgent,
    };

    // Add signature header
    const formattedSignature = signature.signatureFormat
      .replace('{timestamp}', signature.timestamp)
      .replace('{signature}', signature.signature);
    
    headers[this.signatureHeaderName] = formattedSignature;
    headers[this.timestampHeaderName] = signature.timestamp;
    headers[this.idHeaderName] = payload.id;
    headers[this.eventHeaderName] = payload.event;

    // Add authentication headers if configured
    if (webhookConfig.authType === 'basic' && webhookConfig.basicAuth) {
      const auth = Buffer.from(
        `${webhookConfig.basicAuth.username}:${webhookConfig.basicAuth.password}`
      ).toString('base64');
      headers['Authorization'] = `Basic ${auth}`;
    } else if (webhookConfig.authType === 'bearer' && webhookConfig.bearerToken) {
      headers['Authorization'] = `Bearer ${webhookConfig.bearerToken}`;
    } else if (webhookConfig.authType === 'custom' && webhookConfig.customAuth) {
      headers[webhookConfig.customAuth.headerName] = webhookConfig.customAuth.headerValue;
    }

    return headers;
  }

  /**
   * Delivers a webhook payload to the configured endpoint
   * @param webhookConfig The webhook configuration
   * @param payload The webhook payload to deliver
   * @returns The delivery result
   */
  public async deliverWebhook(webhookConfig: IWebhookConfig, payload: IWebhookPayload): Promise<IWebhookDeliveryResult> {
    const deliveryId = uuidv4();
    const startTime = Date.now();
    const timestamp = new Date().toISOString();

    // Initialize delivery result
    const deliveryResult: IWebhookDeliveryResult = {
      id: deliveryId,
      webhookId: webhookConfig.id,
      eventId: payload.id,
      url: webhookConfig.url,
      method: webhookConfig.method,
      requestHeaders: {} as IWebhookHeaders,
      requestPayload: payload,
      success: false,
      timestamp: timestamp,
      durationMs: 0,
      retryCount: 0,
      maxRetries: webhookConfig.retryPolicy.maxRetries,
      willRetry: false
    };

    try {
      // Skip delivery if webhook is not active
      if (webhookConfig.status !== WebhookStatus.ACTIVE) {
        this.logger.info('Skipping webhook delivery - webhook not active', {
          webhookId: webhookConfig.id,
          status: webhookConfig.status,
          deliveryId
        });
        deliveryResult.error = 'Webhook not active';
        deliveryResult.errorCode = 'WEBHOOK_INACTIVE';
        return deliveryResult;
      }

      // Validate payload against schema
      if (!this.validatePayload(payload, payload.event)) {
        this.logger.error('Webhook payload validation failed', {
          webhookId: webhookConfig.id,
          event: payload.event,
          deliveryId
        });
        deliveryResult.error = 'Payload validation failed';
        deliveryResult.errorCode = 'PAYLOAD_VALIDATION_FAILED';
        return deliveryResult;
      }

      // Generate signature
      const signature = this.generateSignature(payload, webhookConfig.secret, timestamp);
      deliveryResult.signature = {
        value: signature.signature,
        timestamp: signature.timestamp,
        algorithm: signature.algorithm
      };

      // Prepare headers
      const headers = this.prepareHeaders(webhookConfig, signature, payload);
      deliveryResult.requestHeaders = headers;

      // Prepare request config
      const requestConfig: AxiosRequestConfig = {
        method: webhookConfig.method,
        url: webhookConfig.url,
        headers,
        timeout: webhookConfig.timeoutMs,
        validateStatus: () => true, // Don't throw on any status code
        httpsAgent: webhookConfig.verifySSL ? undefined : new (require('https').Agent)({ rejectUnauthorized: false })
      };

      // Add payload to request based on method
      if (webhookConfig.method !== WebhookMethod.GET) {
        requestConfig.data = payload;
      }

      this.logger.info('Delivering webhook', {
        webhookId: webhookConfig.id,
        url: webhookConfig.url,
        method: webhookConfig.method,
        event: payload.event,
        deliveryId
      });

      // Send the webhook request
      const response: AxiosResponse = await axios(requestConfig);
      const endTime = Date.now();
      deliveryResult.durationMs = endTime - startTime;

      // Process response
      const webhookResponse: IWebhookResponse = {
        statusCode: response.status,
        headers: response.headers as Record<string, string>,
        body: typeof response.data === 'string' ? response.data : JSON.stringify(response.data),
        success: response.status >= 200 && response.status < 300,
        responseTimeMs: deliveryResult.durationMs,
        timestamp: new Date().toISOString(),
        shouldRetry: this.shouldRetryResponse(response.status, webhookConfig.retryPolicy.retryableStatusCodes)
      };
      deliveryResult.response = webhookResponse;

      // Check if delivery was successful
      if (webhookResponse.success) {
        this.logger.info('Webhook delivered successfully', {
          webhookId: webhookConfig.id,
          deliveryId,
          statusCode: response.status,
          responseTime: deliveryResult.durationMs
        });
        deliveryResult.success = true;
      } else {
        this.logger.warn('Webhook delivery failed', {
          webhookId: webhookConfig.id,
          deliveryId,
          statusCode: response.status,
          responseTime: deliveryResult.durationMs,
          responseBody: webhookResponse.body.substring(0, 200) // Log first 200 chars of response
        });
        deliveryResult.error = `HTTP ${response.status}: ${webhookResponse.body.substring(0, 100)}`;
        deliveryResult.errorCode = `HTTP_${response.status}`;
        deliveryResult.willRetry = webhookResponse.shouldRetry;

        if (webhookResponse.shouldRetry) {
          const nextRetryTime = new Date(Date.now() + this.calculateRetryDelay(0, webhookConfig.retryPolicy));
          deliveryResult.nextRetryAt = nextRetryTime.toISOString();
        }
      }

      return deliveryResult;
    } catch (error) {
      const endTime = Date.now();
      deliveryResult.durationMs = endTime - startTime;

      // Handle network errors and timeouts
      const axiosError = error as AxiosError;
      const errorMessage = axiosError.message || 'Unknown error';
      const isTimeout = errorMessage.includes('timeout');
      const isConnectionError = axiosError.code === 'ECONNREFUSED' || 
                               axiosError.code === 'ECONNABORTED' ||
                               axiosError.code === 'ENOTFOUND';

      this.logger.error('Webhook delivery error', {
        webhookId: webhookConfig.id,
        deliveryId,
        error: errorMessage,
        code: axiosError.code,
        isTimeout,
        isConnectionError
      });

      deliveryResult.error = errorMessage;
      deliveryResult.errorCode = axiosError.code || 'DELIVERY_ERROR';
      
      // Determine if we should retry
      const shouldRetryTimeout = isTimeout && webhookConfig.retryPolicy.retryOnTimeout;
      const shouldRetryConnection = isConnectionError && webhookConfig.retryPolicy.retryOnConnectionError;
      deliveryResult.willRetry = shouldRetryTimeout || shouldRetryConnection;

      if (deliveryResult.willRetry) {
        const nextRetryTime = new Date(Date.now() + this.calculateRetryDelay(0, webhookConfig.retryPolicy));
        deliveryResult.nextRetryAt = nextRetryTime.toISOString();
      }

      return deliveryResult;
    }
  }

  /**
   * Determines if a response should trigger a retry based on status code
   * @param statusCode The HTTP status code
   * @param retryableStatusCodes Array of status codes that should trigger a retry
   * @returns True if the response should be retried, false otherwise
   */
  private shouldRetryResponse(statusCode: number, retryableStatusCodes: number[]): boolean {
    // Common retryable status codes if not explicitly configured
    const defaultRetryableCodes = [408, 429, 500, 502, 503, 504];
    const codesToCheck = retryableStatusCodes?.length ? retryableStatusCodes : defaultRetryableCodes;
    
    return codesToCheck.includes(statusCode);
  }

  /**
   * Calculates the delay before the next retry attempt using exponential backoff
   * @param currentRetry The current retry attempt number (0-based)
   * @param retryPolicy The retry policy configuration
   * @returns The delay in milliseconds before the next retry
   */
  private calculateRetryDelay(currentRetry: number, retryPolicy: IWebhookConfig['retryPolicy']): number {
    if (!retryPolicy.enabled) {
      return 0;
    }

    let delay = retryPolicy.initialDelayMs;

    // Apply exponential backoff if configured
    if (retryPolicy.useExponentialBackoff && currentRetry > 0) {
      delay = Math.min(
        retryPolicy.initialDelayMs * Math.pow(retryPolicy.backoffFactor, currentRetry),
        retryPolicy.maxDelayMs
      );
    }

    // Add jitter to prevent thundering herd problem
    if (retryPolicy.useJitter) {
      const jitterFactor = 0.25; // 25% jitter
      const jitterRange = delay * jitterFactor;
      delay = delay - jitterRange + (Math.random() * jitterRange * 2);
    }

    return Math.floor(delay);
  }

  /**
   * Verifies a webhook signature to ensure it was sent by an authorized sender
   * @param payload The webhook payload
   * @param signature The signature from the request headers
   * @param secret The customer-specific secret key
   * @param timestamp The timestamp from the request headers
   * @returns True if the signature is valid, false otherwise
   */
  public verifySignature(payload: string, signature: string, secret: string, timestamp: string): boolean {
    try {
      // Generate the expected signature
      const hmac = crypto.createHmac('sha256', secret);
      hmac.update(`${timestamp}.${payload}`);
      const expectedSignature = hmac.digest('hex');

      // Use timing-safe comparison to prevent timing attacks
      const signatureBuffer = Buffer.from(signature, 'hex');
      const expectedBuffer = Buffer.from(expectedSignature, 'hex');

      // Ensure buffers are the same length for comparison
      if (signatureBuffer.length !== expectedBuffer.length) {
        return false;
      }

      return crypto.timingSafeEqual(signatureBuffer, expectedBuffer);
    } catch (error) {
      this.logger.error('Error verifying webhook signature', {
        error: (error as Error).message,
        timestamp
      });
      return false;
    }
  }

  /**
   * Parses a signature header value to extract the signature and timestamp
   * @param signatureHeader The signature header value
   * @returns An object containing the signature and timestamp, or null if parsing fails
   */
  public parseSignatureHeader(signatureHeader: string): { signature: string; timestamp: string } | null {
    try {
      // Format: t={timestamp},v1={signature}
      const timestampMatch = signatureHeader.match(/t=([^,]+)/);
      const signatureMatch = signatureHeader.match(/v1=([^,]+)/);

      if (!timestampMatch || !signatureMatch) {
        return null;
      }

      return {
        timestamp: timestampMatch[1],
        signature: signatureMatch[1]
      };
    } catch (error) {
      this.logger.error('Error parsing signature header', {
        error: (error as Error).message,
        signatureHeader
      });
      return null;
    }
  }

  /**
   * Updates a webhook configuration status based on delivery results
   * @param webhookConfig The webhook configuration to update
   * @param deliveryResult The result of the latest delivery attempt
   * @returns The updated webhook configuration
   */
  public updateWebhookStatus(webhookConfig: IWebhookConfig, deliveryResult: IWebhookDeliveryResult): IWebhookConfig {
    const updatedConfig = { ...webhookConfig };
    const now = new Date().toISOString();

    if (deliveryResult.success) {
      // Reset failure count on success
      updatedConfig.consecutiveFailures = 0;
      updatedConfig.lastSuccessAt = now;
      updatedConfig.status = WebhookStatus.ACTIVE;
    } else {
      // Increment failure count
      updatedConfig.consecutiveFailures += 1;
      updatedConfig.lastFailureAt = now;

      // Check if max failures exceeded
      if (updatedConfig.consecutiveFailures >= updatedConfig.maxConsecutiveFailures) {
        updatedConfig.status = WebhookStatus.FAILED;
        this.logger.warn('Webhook marked as failed due to consecutive failures', {
          webhookId: webhookConfig.id,
          consecutiveFailures: updatedConfig.consecutiveFailures,
          maxConsecutiveFailures: updatedConfig.maxConsecutiveFailures
        });
      }
    }

    return updatedConfig;
  }
}