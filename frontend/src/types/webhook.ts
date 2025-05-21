import type { IDateValue } from './common';

// ----------------------------------------------------------------------

/**
 * Enum representing the different types of events that can trigger a webhook.
 */
export enum IWebhookEvent {
  APPLICATION_CREATED = 'application_created',
  APPLICATION_UPDATED = 'application_updated',
  APPLICATION_APPROVED = 'application_approved',
  APPLICATION_REJECTED = 'application_rejected',
  DOCUMENT_UPLOADED = 'document_uploaded',
  DOCUMENT_CLASSIFIED = 'document_classified',
  OCR_COMPLETED = 'ocr_completed',
  FUNDING_INITIATED = 'funding_initiated',
  FUNDING_COMPLETED = 'funding_completed'
}

/**
 * Interface for webhook configuration.
 */
export interface IWebhookConfig {
  id: string;
  url: string;
  description: string;
  events: IWebhookEvent[];
  headers?: Record<string, string>;
  active: boolean;
  createdAt: IDateValue;
  updatedAt: IDateValue;
  createdBy: string;
  secret?: string; // Only visible when creating, not returned in GET requests
}

/**
 * Enum representing the status of a webhook delivery attempt.
 */
export enum IWebhookDeliveryStatus {
  SUCCESS = 'success',
  FAILED = 'failed',
  PENDING = 'pending',
  RETRYING = 'retrying'
}

/**
 * Interface for webhook delivery log entry.
 */
export interface IWebhookDeliveryLog {
  id: string;
  webhookId: string;
  event: IWebhookEvent;
  status: IWebhookDeliveryStatus;
  statusCode?: number;
  requestPayload: string;
  responseBody?: string;
  errorMessage?: string;
  attemptCount: number;
  nextRetry?: IDateValue;
  createdAt: IDateValue;
  completedAt?: IDateValue;
}

/**
 * Interface for webhook test result.
 */
export interface IWebhookTestResult {
  success: boolean;
  statusCode?: number;
  responseBody?: string;
  errorMessage?: string;
  responseTime?: number; // in milliseconds
  timestamp: IDateValue;
}

/**
 * Interface for current webhook status.
 */
export interface IWebhookStatus {
  id: string;
  url: string;
  active: boolean;
  lastTestedAt?: IDateValue;
  lastDeliveryAt?: IDateValue;
  lastDeliveryStatus?: IWebhookDeliveryStatus;
  successRate: number; // percentage of successful deliveries
  totalDeliveries: number;
  successfulDeliveries: number;
  failedDeliveries: number;
}

/**
 * Interface for webhook delivery log filters.
 */
export interface IWebhookFilters {
  webhookId?: string;
  event?: IWebhookEvent;
  status?: IWebhookDeliveryStatus;
  dateFrom?: IDateValue;
  dateTo?: IDateValue;
}

/**
 * Interface for webhook table filters used in the UI.
 */
export interface IWebhookTableFilters {
  name: string;
  status: string[];
  event: string[];
}