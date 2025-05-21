/**
 * Common type definitions for the Email Service
 * 
 * This module defines essential shared TypeScript type aliases used throughout
 * the Email Service microservice. It provides fundamental data structures for
 * consistent date representation, standardized logging, and uniform error handling.
 */

/**
 * Represents a date value with ISO string format
 */
export interface IDateValue {
  /** ISO 8601 formatted date string */
  iso: string;
  
  /** Unix timestamp in milliseconds */
  timestamp: number;
}

/**
 * Log levels for the application
 */
export type LogLevel = 'error' | 'warn' | 'info' | 'debug';

/**
 * Generic result type for operations that can succeed or fail
 */
export interface IResult<T = unknown> {
  /** Whether the operation succeeded */
  success: boolean;
  
  /** Result data if successful */
  data?: T;
  
  /** Error information if failed */
  error?: {
    message: string;
    code?: string;
    details?: unknown;
  };
}

/**
 * Async operation result with timing information
 */
export interface IAsyncOperationResult<T = unknown> extends IResult<T> {
  /** Operation timing information */
  timing: {
    /** When the operation started */
    startTime: number;
    
    /** When the operation completed */
    endTime: number;
    
    /** Duration in milliseconds */
    duration: number;
  };
}

/**
 * Health check status
 */
export enum HealthStatus {
  /** Service is healthy and fully operational */
  HEALTHY = 'healthy',
  
  /** Service is degraded but still operational */
  DEGRADED = 'degraded',
  
  /** Service is unhealthy and not operational */
  UNHEALTHY = 'unhealthy'
}

/**
 * Health check result
 */
export interface IHealthCheckResult {
  /** Overall service status */
  status: HealthStatus;
  
  /** Timestamp of the health check */
  timestamp: string;
  
  /** Service name */
  service: string;
  
  /** Service version */
  version: string;
  
  /** Component-specific health status */
  components: Record<string, {
    status: HealthStatus;
    message?: string;
    details?: Record<string, unknown>;
  }>;
}