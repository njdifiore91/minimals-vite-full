import type { Dayjs } from 'dayjs';

// ----------------------------------------------------------------------

/**
 * Interface for consistent date representation across the service
 * Can be a string (ISO format), number (timestamp) or null
 */
export type IDateValue = string | number | null;

/**
 * Interface for date picker control using Day.js
 */
export type IDatePickerControl = Dayjs | null;

/**
 * Interface for structured logging with correlation IDs and metadata
 * Used for cross-service tracing as specified in section 3.2.3
 */
export interface ILogContext {
  /** Unique request identifier for cross-service tracing */
  correlationId: string;
  /** Service name generating the log */
  serviceName: string;
  /** Optional user identifier if request is authenticated */
  userId?: string;
  /** Timestamp when the log was created */
  timestamp: IDateValue;
  /** Additional metadata for the log entry */
  metadata?: Record<string, unknown>;
}

/**
 * Interface for standardized error responses
 * Provides consistent error format across all API endpoints
 */
export interface IErrorResponse {
  /** HTTP status code */
  statusCode: number;
  /** Error message */
  message: string;
  /** Error code for client-side error handling */
  errorCode: string;
  /** Correlation ID for tracing the request */
  correlationId: string;
  /** Timestamp when the error occurred */
  timestamp: IDateValue;
  /** Optional additional details about the error */
  details?: Record<string, unknown>;
}

/**
 * Interface for health check responses
 * Used for Kubernetes probes as specified in section 3.2.3
 */
export interface IServiceStatus {
  /** Service name */
  service: string;
  /** Service status: 'healthy', 'degraded', or 'unhealthy' */
  status: 'healthy' | 'degraded' | 'unhealthy';
  /** Version of the service */
  version: string;
  /** Timestamp of the status check */
  timestamp: IDateValue;
  /** Optional details about service dependencies */
  dependencies?: {
    /** Name of the dependency */
    name: string;
    /** Status of the dependency */
    status: 'healthy' | 'degraded' | 'unhealthy';
    /** Optional details about the dependency */
    details?: string;
  }[];
}

/**
 * Interface for configuring retry behavior with backoff settings
 * Used for webhook delivery retry mechanism as specified in section 4.1.10
 */
export interface IRetryOptions {
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Initial delay in milliseconds before the first retry */
  initialDelayMs: number;
  /** Maximum delay in milliseconds between retries */
  maxDelayMs: number;
  /** Backoff factor for exponential backoff calculation */
  backoffFactor: number;
  /** Whether to add jitter to the delay to prevent thundering herd */
  useJitter: boolean;
  /** Optional timeout in milliseconds for each retry attempt */
  timeoutMs?: number;
}

/**
 * Interface for payment card information
 */
export type IPaymentCard = {
  id: string;
  cardType: string;
  primary?: boolean;
  cardNumber: string;
};

/**
 * Interface for address information
 */
export type IAddressItem = {
  id?: string;
  name: string;
  company?: string;
  primary?: boolean;
  fullAddress: string;
  phoneNumber?: string;
  addressType?: string;
};

/**
 * Interface for social media links
 */
export type ISocialLink = {
  twitter: string;
  facebook: string;
  linkedin: string;
  instagram: string;
};