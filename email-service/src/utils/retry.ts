/**
 * Retry Utility Module
 * 
 * Provides retry logic utilities for the Email Service with exponential backoff, jitter,
 * and configurable limits. Essential for handling temporary failures in external service
 * connections and ensuring reliable operation.
 */

/**
 * Configuration options for retry operations
 */
export interface RetryOptions {
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Initial delay in milliseconds before the first retry */
  initialDelayMs: number;
  /** Maximum delay in milliseconds between retries */
  maxDelayMs: number;
  /** Factor by which the delay increases with each retry */
  backoffFactor: number;
  /** Maximum jitter percentage (0-1) to add to delay to prevent thundering herd */
  jitterFactor: number;
  /** Optional function to determine if an error is eligible for retry */
  isRetryable?: (error: Error) => boolean;
  /** Optional callback function to execute before each retry attempt */
  onRetry?: (attempt: number, delay: number, error: Error) => void;
}

/**
 * Default retry options
 */
export const DEFAULT_RETRY_OPTIONS: RetryOptions = {
  maxRetries: 3,
  initialDelayMs: 1000, // 1 second
  maxDelayMs: 30000, // 30 seconds
  backoffFactor: 2,
  jitterFactor: 0.2, // 20% jitter
};

/**
 * Result of a retry operation
 */
export interface RetryResult<T> {
  /** The result of the successful operation */
  result?: T;
  /** The error if all retries failed */
  error?: Error;
  /** Number of retry attempts made */
  attempts: number;
  /** Whether the operation was successful */
  success: boolean;
  /** Total time spent in retry operations (ms) */
  totalTimeMs?: number;
}

/**
 * Common error types that are typically retryable
 */
export enum RetryableErrorType {
  /** Network connectivity issues */
  NETWORK = 'network',
  /** Server overload or temporary unavailability */
  SERVER_BUSY = 'server_busy',
  /** Rate limiting or throttling */
  RATE_LIMIT = 'rate_limit',
  /** Temporary service unavailability */
  SERVICE_UNAVAILABLE = 'service_unavailable',
  /** Connection timeout */
  TIMEOUT = 'timeout',
  /** Database connection issues */
  DATABASE = 'database',
  /** Message queue connection issues */
  QUEUE = 'queue',
  /** Storage service connection issues */
  STORAGE = 'storage',
  /** IMAP connection issues */
  IMAP = 'imap',
}

/**
 * Error types that should not be retried
 */
export enum NonRetryableErrorType {
  /** Authentication failures */
  AUTHENTICATION = 'authentication',
  /** Authorization failures */
  AUTHORIZATION = 'authorization',
  /** Invalid request format or parameters */
  VALIDATION = 'validation',
  /** Resource not found */
  NOT_FOUND = 'not_found',
  /** Business logic errors */
  BUSINESS_LOGIC = 'business_logic',
  /** Internal server errors that are not transient */
  INTERNAL = 'internal',
  /** Malformed message or document */
  MALFORMED = 'malformed',
  /** Virus or security threat detected */
  SECURITY = 'security',
}

/**
 * Determines if an error is retryable based on its type or properties
 * 
 * @param error - The error to check
 * @returns True if the error is retryable, false otherwise
 */
export function isRetryableError(error: Error): boolean {
  // Check for network errors (common in Node.js)
  if (
    error.message.includes('ECONNREFUSED') ||
    error.message.includes('ECONNRESET') ||
    error.message.includes('ETIMEDOUT') ||
    error.message.includes('EHOSTUNREACH') ||
    error.message.includes('ENETUNREACH') ||
    error.message.includes('socket hang up') ||
    error.message.includes('network error')
  ) {
    return true;
  }

  // Check for HTTP status codes that indicate retryable errors
  if (
    error.message.includes('status code 429') || // Too Many Requests
    error.message.includes('status code 503') || // Service Unavailable
    error.message.includes('status code 502') || // Bad Gateway
    error.message.includes('status code 504')    // Gateway Timeout
  ) {
    return true;
  }

  // Check for custom error type property if it exists
  const anyError = error as any;
  if (anyError.type && Object.values(RetryableErrorType).includes(anyError.type)) {
    return true;
  }

  // Check for IMAP-specific errors
  if (
    error.message.includes('IMAP connection') ||
    error.message.includes('imap failure') ||
    error.message.includes('connection closed') ||
    error.message.includes('connection dropped')
  ) {
    return true;
  }

  // Check for RabbitMQ-specific errors
  if (
    error.message.includes('AMQP connection') ||
    error.message.includes('channel closed') ||
    error.message.includes('connection closed')
  ) {
    return true;
  }

  // Check for S3/storage-specific errors
  if (
    error.message.includes('SlowDown') ||
    error.message.includes('RequestTimeout') ||
    error.message.includes('RequestTimeTooSkewed') ||
    error.message.includes('OperationAborted')
  ) {
    return true;
  }

  return false;
}

/**
 * Calculates the delay for the next retry attempt using exponential backoff with jitter
 * 
 * @param attempt - The current attempt number (0-based)
 * @param options - The retry options
 * @returns The delay in milliseconds before the next retry
 */
export function calculateBackoff(attempt: number, options: RetryOptions): number {
  // Calculate base delay with exponential backoff
  const exponentialDelay = options.initialDelayMs * Math.pow(options.backoffFactor, attempt);
  
  // Apply maximum delay cap
  const cappedDelay = Math.min(exponentialDelay, options.maxDelayMs);
  
  // Apply jitter to prevent thundering herd problem
  // Formula: delay = baseDelay * (1 - jitterFactor/2 + random * jitterFactor)
  // This creates a range of [baseDelay * (1 - jitterFactor/2), baseDelay * (1 + jitterFactor/2)]
  const jitterMultiplier = 1 - options.jitterFactor / 2 + Math.random() * options.jitterFactor;
  
  // Return the final delay with jitter applied
  return Math.floor(cappedDelay * jitterMultiplier);
}

/**
 * Creates a promise that resolves after the specified delay
 * 
 * @param ms - The delay in milliseconds
 * @returns A promise that resolves after the delay
 */
export function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Executes a function with retry logic
 * 
 * @param fn - The function to execute with retry logic
 * @param options - The retry options
 * @returns A promise that resolves with the retry result
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  options: Partial<RetryOptions> = {}
): Promise<RetryResult<T>> {
  // Merge provided options with defaults
  const retryOptions: RetryOptions = {
    ...DEFAULT_RETRY_OPTIONS,
    ...options,
  };

  let attempts = 0;
  let lastError: Error | undefined;
  const startTime = Date.now();

  while (attempts <= retryOptions.maxRetries) {
    try {
      // If this isn't the first attempt, apply delay
      if (attempts > 0) {
        const delayMs = calculateBackoff(attempts - 1, retryOptions);
        
        // Call onRetry callback if provided
        if (retryOptions.onRetry && lastError) {
          retryOptions.onRetry(attempts, delayMs, lastError);
        }
        
        await delay(delayMs);
      }

      // Attempt to execute the function
      const result = await fn();
      
      // If successful, return the result
      return {
        result,
        attempts,
        success: true,
        totalTimeMs: Date.now() - startTime,
      };
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      attempts++;

      // Check if we've exhausted all retry attempts
      if (attempts > retryOptions.maxRetries) {
        break;
      }

      // Check if the error is retryable
      const isRetryableFn = retryOptions.isRetryable || isRetryableError;
      if (!isRetryableFn(lastError)) {
        break;
      }
    }
  }

  // If we get here, all retries failed
  return {
    error: lastError,
    attempts,
    success: false,
    totalTimeMs: Date.now() - startTime,
  };
}

/**
 * Creates a retryable version of an async function
 * 
 * @param fn - The function to make retryable
 * @param options - The retry options
 * @returns A wrapped function that will retry on failure
 */
export function createRetryableFunction<T, Args extends any[]>(
  fn: (...args: Args) => Promise<T>,
  options: Partial<RetryOptions> = {}
): (...args: Args) => Promise<T> {
  return async (...args: Args): Promise<T> => {
    const result = await withRetry(() => fn(...args), options);
    
    if (!result.success) {
      throw result.error;
    }
    
    return result.result as T;
  };
}

/**
 * Retry decorator for class methods
 * 
 * @param options - The retry options
 * @returns A method decorator that adds retry logic
 */
export function retryable(options: Partial<RetryOptions> = {}) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;
    
    descriptor.value = async function (...args: any[]) {
      const result = await withRetry(() => originalMethod.apply(this, args), options);
      
      if (!result.success) {
        throw result.error;
      }
      
      return result.result;
    };
    
    return descriptor;
  };
}

/**
 * Executes a function with retry logic and custom error handling
 * 
 * @param fn - The function to execute
 * @param errorHandler - Custom error handler function
 * @param options - The retry options
 * @returns A promise that resolves with the function result or the error handler result
 */
export async function withRetryOrElse<T, E>(
  fn: () => Promise<T>,
  errorHandler: (error: Error, attempts: number) => Promise<E>,
  options: Partial<RetryOptions> = {}
): Promise<T | E> {
  const result = await withRetry(fn, options);
  
  if (result.success) {
    return result.result as T;
  }
  
  return errorHandler(result.error as Error, result.attempts);
}

/**
 * Executes a function with retry logic and fallback value
 * 
 * @param fn - The function to execute
 * @param fallbackValue - Value to return if all retries fail
 * @param options - The retry options
 * @returns A promise that resolves with the function result or the fallback value
 */
export async function withRetryOrDefault<T>(
  fn: () => Promise<T>,
  fallbackValue: T,
  options: Partial<RetryOptions> = {}
): Promise<T> {
  const result = await withRetry(fn, options);
  
  if (result.success) {
    return result.result as T;
  }
  
  return fallbackValue;
}

/**
 * Specialized retry options for IMAP connections
 */
export const IMAP_RETRY_OPTIONS: RetryOptions = {
  maxRetries: 5,
  initialDelayMs: 2000, // 2 seconds
  maxDelayMs: 60000, // 60 seconds
  backoffFactor: 2,
  jitterFactor: 0.2,
  isRetryable: (error: Error) => {
    // IMAP-specific retry logic
    return (
      error.message.includes('IMAP connection') ||
      error.message.includes('imap failure') ||
      error.message.includes('connection closed') ||
      error.message.includes('connection dropped') ||
      error.message.includes('socket hang up') ||
      error.message.includes('ECONNRESET') ||
      error.message.includes('ETIMEDOUT')
    );
  },
};

/**
 * Specialized retry options for RabbitMQ connections
 */
export const RABBITMQ_RETRY_OPTIONS: RetryOptions = {
  maxRetries: 10,
  initialDelayMs: 1000, // 1 second
  maxDelayMs: 30000, // 30 seconds
  backoffFactor: 1.5,
  jitterFactor: 0.25,
  isRetryable: (error: Error) => {
    // RabbitMQ-specific retry logic
    return (
      error.message.includes('AMQP connection') ||
      error.message.includes('channel closed') ||
      error.message.includes('connection closed') ||
      error.message.includes('socket hang up') ||
      error.message.includes('ECONNREFUSED') ||
      error.message.includes('ECONNRESET') ||
      error.message.includes('ETIMEDOUT')
    );
  },
};

/**
 * Specialized retry options for S3 storage operations
 */
export const S3_RETRY_OPTIONS: RetryOptions = {
  maxRetries: 5,
  initialDelayMs: 1000, // 1 second
  maxDelayMs: 15000, // 15 seconds
  backoffFactor: 2,
  jitterFactor: 0.3,
  isRetryable: (error: Error) => {
    // S3-specific retry logic
    return (
      error.message.includes('SlowDown') ||
      error.message.includes('RequestTimeout') ||
      error.message.includes('RequestTimeTooSkewed') ||
      error.message.includes('OperationAborted') ||
      error.message.includes('InternalError') ||
      error.message.includes('ServiceUnavailable') ||
      error.message.includes('ECONNRESET') ||
      error.message.includes('ETIMEDOUT') ||
      error.message.includes('EPIPE')
    );
  },
};