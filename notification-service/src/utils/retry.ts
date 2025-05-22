/**
 * Retry utility for implementing exponential backoff for webhook deliveries
 * 
 * This module provides utilities for calculating retry intervals, tracking retry attempts,
 * and scheduling retries with configurable parameters. It implements an exponential backoff
 * algorithm with jitter to prevent the "thundering herd" problem.
 */

import dayjs from 'dayjs';

/**
 * Configuration options for the retry mechanism
 */
export interface RetryOptions {
  /** Base delay in milliseconds before applying exponential factor */
  baseDelayMs: number;
  /** Exponential factor to multiply by attempt number */
  exponentialFactor: number;
  /** Maximum delay in milliseconds */
  maxDelayMs: number;
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Jitter factor (0-1) to randomize delay and prevent thundering herd */
  jitterFactor: number;
}

/**
 * Default retry configuration
 */
export const DEFAULT_RETRY_OPTIONS: RetryOptions = {
  baseDelayMs: 1000, // 1 second
  exponentialFactor: 2,
  maxDelayMs: 60000, // 1 minute
  maxRetries: 5,
  jitterFactor: 0.2, // 20% jitter
};

/**
 * Retry state for tracking attempts and scheduling
 */
export interface RetryState {
  /** Current retry attempt number (0-based) */
  attempt: number;
  /** Timestamp when the next retry should occur */
  nextRetryTime: number | null;
  /** Whether the retry limit has been reached */
  exhausted: boolean;
  /** History of retry timestamps */
  retryHistory: number[];
  /** Original error that triggered the retry */
  originalError?: Error;
  /** Last error encountered during retry */
  lastError?: Error;
}

/**
 * Creates a new retry state
 */
export function createRetryState(originalError?: Error): RetryState {
  return {
    attempt: 0,
    nextRetryTime: null,
    exhausted: false,
    retryHistory: [],
    originalError,
  };
}

/**
 * Calculates the delay for the next retry attempt using exponential backoff
 * 
 * @param attempt Current retry attempt number (0-based)
 * @param options Retry configuration options
 * @returns Delay in milliseconds for the next retry
 */
export function calculateBackoffDelay(
  attempt: number,
  options: RetryOptions = DEFAULT_RETRY_OPTIONS
): number {
  // Ensure attempt is at least 0
  const retryAttempt = Math.max(0, attempt);
  
  // Calculate exponential backoff: baseDelay * (exponentialFactor ^ attempt)
  const exponentialDelay = options.baseDelayMs * Math.pow(options.exponentialFactor, retryAttempt);
  
  // Cap the delay at the maximum allowed delay
  const cappedDelay = Math.min(exponentialDelay, options.maxDelayMs);
  
  return cappedDelay;
}

/**
 * Adds jitter to the delay to prevent thundering herd problem
 * 
 * @param delay Base delay in milliseconds
 * @param jitterFactor Factor to determine jitter amount (0-1)
 * @returns Delay with jitter applied
 */
export function applyJitter(
  delay: number,
  jitterFactor: number = DEFAULT_RETRY_OPTIONS.jitterFactor
): number {
  // Ensure jitter factor is between 0 and 1
  const factor = Math.max(0, Math.min(1, jitterFactor));
  
  // Calculate jitter range (delay * jitterFactor)
  const jitterRange = delay * factor;
  
  // Generate random jitter within range: -jitterRange/2 to +jitterRange/2
  const jitter = (Math.random() - 0.5) * jitterRange;
  
  // Apply jitter to delay
  return Math.max(0, delay + jitter);
}

/**
 * Calculates the next retry time with exponential backoff and jitter
 * 
 * @param attempt Current retry attempt number (0-based)
 * @param options Retry configuration options
 * @returns Timestamp in milliseconds when the next retry should occur
 */
export function calculateNextRetryTime(
  attempt: number,
  options: RetryOptions = DEFAULT_RETRY_OPTIONS
): number {
  const backoffDelay = calculateBackoffDelay(attempt, options);
  const delayWithJitter = applyJitter(backoffDelay, options.jitterFactor);
  
  // Calculate next retry time by adding delay to current time
  return Date.now() + delayWithJitter;
}

/**
 * Determines if a retry is eligible based on attempt count and options
 * 
 * @param state Current retry state
 * @param options Retry configuration options
 * @returns Whether a retry is eligible
 */
export function isRetryEligible(
  state: RetryState,
  options: RetryOptions = DEFAULT_RETRY_OPTIONS
): boolean {
  return state.attempt < options.maxRetries;
}

/**
 * Determines if an error is retryable based on its type and status code
 * 
 * @param error Error to check
 * @returns Whether the error is retryable
 */
export function isErrorRetryable(error: any): boolean {
  // Network errors are generally retryable
  if (error?.code === 'ECONNRESET' || 
      error?.code === 'ETIMEDOUT' || 
      error?.code === 'ECONNREFUSED' || 
      error?.code === 'ENOTFOUND') {
    return true;
  }
  
  // For HTTP errors, check status code
  // 429 (Too Many Requests) and 5xx errors are retryable
  if (error?.response?.status) {
    const statusCode = error.response.status;
    return statusCode === 429 || (statusCode >= 500 && statusCode < 600);
  }
  
  // Default to not retryable for unknown error types
  return false;
}

/**
 * Updates the retry state for the next attempt
 * 
 * @param state Current retry state
 * @param error Error from the failed attempt
 * @param options Retry configuration options
 * @returns Updated retry state
 */
export function prepareForNextRetry(
  state: RetryState,
  error: Error,
  options: RetryOptions = DEFAULT_RETRY_OPTIONS
): RetryState {
  // Increment attempt counter
  const nextAttempt = state.attempt + 1;
  
  // Calculate next retry time
  const nextRetryTime = calculateNextRetryTime(nextAttempt, options);
  
  // Check if retry limit has been reached
  const exhausted = nextAttempt >= options.maxRetries;
  
  // Update retry history
  const retryHistory = [...state.retryHistory, Date.now()];
  
  return {
    ...state,
    attempt: nextAttempt,
    nextRetryTime: exhausted ? null : nextRetryTime,
    exhausted,
    retryHistory,
    lastError: error,
    originalError: state.originalError || error,
  };
}

/**
 * Formats a retry state for logging
 * 
 * @param state Retry state to format
 * @returns Formatted retry information for logging
 */
export function formatRetryForLogging(state: RetryState): Record<string, any> {
  return {
    attempt: state.attempt,
    nextRetryTime: state.nextRetryTime ? new Date(state.nextRetryTime).toISOString() : null,
    exhausted: state.exhausted,
    retryCount: state.retryHistory.length,
    retryHistory: state.retryHistory.map(time => new Date(time).toISOString()),
    errorMessage: state.lastError?.message || state.originalError?.message,
    errorType: state.lastError?.constructor.name || state.originalError?.constructor.name,
  };
}

/**
 * Calculates the time remaining until the next retry
 * 
 * @param state Current retry state
 * @returns Time remaining in milliseconds, or null if no retry is scheduled
 */
export function getTimeUntilNextRetry(state: RetryState): number | null {
  if (!state.nextRetryTime) {
    return null;
  }
  
  const timeRemaining = state.nextRetryTime - Date.now();
  return Math.max(0, timeRemaining);
}

/**
 * Checks if it's time to execute the next retry
 * 
 * @param state Current retry state
 * @returns Whether it's time to retry
 */
export function isTimeToRetry(state: RetryState): boolean {
  if (!state.nextRetryTime || state.exhausted) {
    return false;
  }
  
  return Date.now() >= state.nextRetryTime;
}

/**
 * Creates a promise that resolves after the next retry delay
 * 
 * @param state Current retry state
 * @returns Promise that resolves when it's time to retry
 */
export function waitForNextRetry(state: RetryState): Promise<void> {
  const timeRemaining = getTimeUntilNextRetry(state);
  
  if (timeRemaining === null || timeRemaining <= 0) {
    return Promise.resolve();
  }
  
  return new Promise(resolve => setTimeout(resolve, timeRemaining));
}

/**
 * Executes a function with retry logic
 * 
 * @param fn Function to execute with retry logic
 * @param options Retry configuration options
 * @returns Promise that resolves with the function result or rejects after all retries fail
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  options: RetryOptions = DEFAULT_RETRY_OPTIONS
): Promise<T> {
  let state = createRetryState();
  
  while (true) {
    try {
      // Attempt to execute the function
      return await fn();
    } catch (error: any) {
      // Check if the error is retryable
      if (!isErrorRetryable(error)) {
        throw error;
      }
      
      // Update retry state
      state = prepareForNextRetry(state, error, options);
      
      // Check if we've exhausted all retries
      if (state.exhausted) {
        throw state.lastError || new Error('Retry limit exceeded');
      }
      
      // Wait until the next retry time
      await waitForNextRetry(state);
    }
  }
}