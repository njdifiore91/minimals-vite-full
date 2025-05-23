/**
 * Retry Utilities
 * 
 * This file provides utility functions for implementing an exponential backoff retry mechanism
 * for failed webhook deliveries. It includes functions for calculating retry intervals,
 * tracking retry attempts, and scheduling retries with configurable parameters.
 * 
 * These utilities are critical for ensuring reliable notification delivery even when
 * recipients are temporarily unavailable, as specified in section 4.1.10 of the technical
 * specification.
 */

/**
 * Interface for configuring retry behavior with exponential backoff
 */
export interface RetryOptions {
  /** Base delay in milliseconds before applying exponential backoff */
  baseDelayMs: number;
  /** Factor to multiply the delay by for each subsequent retry */
  exponentialFactor: number;
  /** Maximum delay in milliseconds between retries */
  maxDelayMs: number;
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Factor to apply for jitter (0-1, where 0 means no jitter) */
  jitterFactor: number;
}

/**
 * Interface for tracking retry state
 */
export interface RetryState {
  /** Current retry attempt (0 for initial attempt) */
  attempt: number;
  /** Timestamp for the next retry attempt */
  nextRetryTime: number | null;
  /** Whether retry attempts have been exhausted */
  exhausted: boolean;
  /** Error from the last attempt */
  lastError: Error | null;
  /** History of retry timestamps */
  retryHistory: number[];
  /** Additional metadata for the retry state */
  metadata?: Record<string, any>;
}

/**
 * Creates a new retry state
 * 
 * @param error Optional error from the initial attempt
 * @returns A new retry state object
 */
export function createRetryState(error: Error | null = null): RetryState {
  return {
    attempt: 0,
    nextRetryTime: null,
    exhausted: false,
    lastError: error,
    retryHistory: [],
    metadata: {},
  };
}

/**
 * Calculates the next retry time using exponential backoff
 * 
 * @param attempt Current retry attempt (0-based)
 * @param options Retry options for configuration
 * @returns Timestamp in milliseconds for the next retry
 */
export function calculateNextRetryTime(attempt: number, options: RetryOptions): number {
  // Calculate base delay with exponential backoff
  // For attempt 0, use baseDelayMs directly
  // For subsequent attempts, apply exponential backoff
  const exponentialDelay = attempt === 0
    ? options.baseDelayMs
    : options.baseDelayMs * Math.pow(options.exponentialFactor, attempt);
  
  // Cap the delay at the maximum delay
  const cappedDelay = Math.min(exponentialDelay, options.maxDelayMs);
  
  // Apply jitter to prevent thundering herd problem
  // Jitter is a random value between (1 - jitterFactor) and (1 + jitterFactor)
  // For example, with jitterFactor = 0.2, jitter will be between 0.8 and 1.2
  const jitter = options.jitterFactor > 0
    ? 1 + (Math.random() * 2 - 1) * options.jitterFactor
    : 1;
  
  // Apply jitter to the capped delay
  const finalDelay = Math.floor(cappedDelay * jitter);
  
  // Calculate the next retry time by adding the delay to the current time
  return Date.now() + finalDelay;
}

/**
 * Checks if retry attempts have been exhausted
 * 
 * @param state Current retry state
 * @param options Retry options for configuration
 * @returns True if retry attempts have been exhausted, false otherwise
 */
export function isRetryExhausted(state: RetryState, options: RetryOptions): boolean {
  return state.attempt >= options.maxRetries;
}

/**
 * Prepares the retry state for the next retry attempt
 * 
 * @param state Current retry state
 * @param error Error from the current attempt
 * @param options Retry options for configuration
 * @returns Updated retry state for the next attempt
 */
export function prepareForNextRetry(
  state: RetryState,
  error: Error,
  options: RetryOptions
): RetryState {
  // Increment the attempt counter
  const nextAttempt = state.attempt + 1;
  
  // Check if retry attempts have been exhausted
  const exhausted = nextAttempt > options.maxRetries;
  
  // Calculate the next retry time if not exhausted
  const nextRetryTime = exhausted ? null : calculateNextRetryTime(nextAttempt, options);
  
  // Update the retry history
  const retryHistory = [...state.retryHistory];
  if (nextRetryTime) {
    retryHistory.push(nextRetryTime);
  }
  
  // Return the updated retry state
  return {
    attempt: nextAttempt,
    nextRetryTime,
    exhausted,
    lastError: error,
    retryHistory,
    metadata: {
      ...state.metadata,
      lastErrorMessage: error.message,
      lastErrorType: error.constructor.name,
      lastErrorTime: Date.now(),
    },
  };
}

/**
 * Determines if a retry should be attempted based on the error
 * 
 * @param error Error from the current attempt
 * @returns True if a retry should be attempted, false otherwise
 */
export function shouldRetry(error: Error): boolean {
  // Network errors should always be retried
  if (error.name === 'NetworkError' || error.name === 'FetchError' || error.name === 'AbortError') {
    return true;
  }
  
  // Timeout errors should be retried
  if (error.name === 'TimeoutError' || error.message.includes('timeout')) {
    return true;
  }
  
  // HTTP errors with status codes 429 (Too Many Requests) or 5xx should be retried
  if (error instanceof Error && 'status' in error) {
    const status = (error as any).status;
    return status === 429 || (status >= 500 && status < 600);
  }
  
  // For other errors, check if they are transient based on the message
  const transientErrorPatterns = [
    'ECONNRESET',
    'ECONNREFUSED',
    'ETIMEDOUT',
    'EHOSTUNREACH',
    'ENETUNREACH',
    'ENOTFOUND',
    'socket hang up',
    'network error',
    'server error',
    'gateway timeout',
    'service unavailable',
    'too many requests',
    'request failed',
    'connection closed',
  ];
  
  return transientErrorPatterns.some(pattern => 
    error.message.toLowerCase().includes(pattern.toLowerCase())
  );
}

/**
 * Determines if an HTTP status code is retryable
 * 
 * @param statusCode HTTP status code
 * @returns True if the status code is retryable, false otherwise
 */
export function isRetryableStatusCode(statusCode: number): boolean {
  // 429 Too Many Requests - should be retried after a delay
  if (statusCode === 429) {
    return true;
  }
  
  // 5xx Server Errors - should be retried
  if (statusCode >= 500 && statusCode < 600) {
    return true;
  }
  
  // 408 Request Timeout - should be retried
  if (statusCode === 408) {
    return true;
  }
  
  // All other status codes are not retryable
  return false;
}

/**
 * Formats retry state for logging
 * 
 * @param state Retry state to format
 * @returns Formatted retry state for logging
 */
export function formatRetryForLogging(state: RetryState): Record<string, any> {
  return {
    attempt: state.attempt,
    nextRetryTime: state.nextRetryTime ? new Date(state.nextRetryTime).toISOString() : null,
    exhausted: state.exhausted,
    lastErrorMessage: state.lastError?.message,
    lastErrorType: state.lastError?.constructor.name,
    retryHistory: state.retryHistory.map(time => new Date(time).toISOString()),
  };
}

/**
 * Calculates exponential backoff delay without applying jitter
 * Useful for displaying predictable retry times to users
 * 
 * @param attempt Current retry attempt (0-based)
 * @param options Retry options for configuration
 * @returns Delay in milliseconds for the given attempt
 */
export function calculateBackoffDelay(attempt: number, options: RetryOptions): number {
  if (attempt === 0) {
    return options.baseDelayMs;
  }
  
  const exponentialDelay = options.baseDelayMs * Math.pow(options.exponentialFactor, attempt);
  return Math.min(exponentialDelay, options.maxDelayMs);
}

/**
 * Formats a retry delay in a human-readable format
 * 
 * @param delayMs Delay in milliseconds
 * @returns Human-readable delay string
 */
export function formatRetryDelay(delayMs: number): string {
  if (delayMs < 1000) {
    return `${delayMs}ms`;
  }
  
  if (delayMs < 60000) {
    return `${Math.round(delayMs / 1000)}s`;
  }
  
  return `${Math.round(delayMs / 60000)}m`;
}

/**
 * Calculates all retry delays for a given configuration
 * Useful for displaying the retry schedule to users or for testing
 * 
 * @param options Retry options for configuration
 * @returns Array of delays in milliseconds for each retry attempt
 */
export function calculateRetrySchedule(options: RetryOptions): number[] {
  const schedule: number[] = [];
  
  for (let attempt = 0; attempt <= options.maxRetries; attempt++) {
    schedule.push(calculateBackoffDelay(attempt, options));
  }
  
  return schedule;
}

/**
 * Estimates the total time required for all retry attempts
 * 
 * @param options Retry options for configuration
 * @returns Total time in milliseconds for all retry attempts
 */
export function estimateTotalRetryTime(options: RetryOptions): number {
  return calculateRetrySchedule(options).reduce((sum, delay) => sum + delay, 0);
}

/**
 * Creates a default retry options object with recommended values
 * 
 * @returns Default retry options
 */
export function createDefaultRetryOptions(): RetryOptions {
  return {
    baseDelayMs: 1000,        // Start with 1 second delay
    exponentialFactor: 2,     // Double the delay each time
    maxDelayMs: 60000,        // Cap at 1 minute
    maxRetries: 5,            // Try up to 5 times
    jitterFactor: 0.2,        // Add 20% jitter
  };
}