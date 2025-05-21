/**
 * Retry Utility
 * 
 * Provides retry logic with exponential backoff and jitter for handling temporary failures
 * in external service connections. This utility is used throughout the Email Service for
 * IMAP connections, RabbitMQ publishing, and S3 storage operations.
 * 
 * Key features:
 * - Exponential backoff with configurable parameters
 * - Random jitter to prevent thundering herd problems
 * - Intelligent retry eligibility based on error type
 * - Promise-based API for async operations
 * - Configurable retry limits and delay caps
 * - Callback hooks for monitoring and logging retry attempts
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
  /** Factor by which the delay increases with each retry attempt */
  backoffFactor: number;
  /** Maximum jitter percentage (0-1) to add to the delay to prevent thundering herd */
  jitterFactor: number;
  /** Optional function to determine if an error is retryable */
  isRetryable?: (error: Error) => boolean;
  /** Optional function to execute before each retry attempt */
  onRetry?: (error: Error, attempt: number, delay: number) => void;
}

/**
 * Default retry configuration
 * 
 * These defaults provide a reasonable starting point for most operations:
 * - 3 retry attempts (4 total attempts including the initial try)
 * - 1 second initial delay, doubling with each retry (1s, 2s, 4s)
 * - 30 second maximum delay cap to prevent excessive waiting
 * - 20% jitter to randomize retry timing and prevent thundering herd
 */
export const DEFAULT_RETRY_OPTIONS: RetryOptions = {
  maxRetries: 3,
  initialDelayMs: 1000, // 1 second
  maxDelayMs: 30000, // 30 seconds
  backoffFactor: 2,
  jitterFactor: 0.2, // 20% jitter
};

/**
 * Aggressive retry configuration for critical operations
 * 
 * Use this configuration for operations that must eventually succeed,
 * such as saving critical data or sending important notifications.
 */
export const AGGRESSIVE_RETRY_OPTIONS: RetryOptions = {
  maxRetries: 10,
  initialDelayMs: 500, // 0.5 seconds
  maxDelayMs: 60000, // 60 seconds
  backoffFactor: 1.5,
  jitterFactor: 0.1, // 10% jitter
};

/**
 * Conservative retry configuration for non-critical operations
 * 
 * Use this configuration for operations where retries should be limited,
 * such as user-facing requests or operations with side effects.
 */
export const CONSERVATIVE_RETRY_OPTIONS: RetryOptions = {
  maxRetries: 2,
  initialDelayMs: 2000, // 2 seconds
  maxDelayMs: 10000, // 10 seconds
  backoffFactor: 2,
  jitterFactor: 0.3, // 30% jitter
};

/**
 * Common retryable error types for network and connection issues
 * 
 * These error codes typically indicate temporary network issues that may be resolved
 * by retrying the operation after a delay.
 */
export const RETRYABLE_ERROR_TYPES = [
  'ECONNRESET',    // Connection reset by peer
  'ECONNREFUSED',  // Connection refused
  'ETIMEDOUT',     // Operation timed out
  'ESOCKETTIMEDOUT', // Socket timeout
  'ENOTFOUND',     // DNS lookup failed
  'ENETUNREACH',   // Network unreachable
  'EAI_AGAIN',     // Temporary DNS resolution failure
  'EPIPE',         // Broken pipe
  'ECONNABORTED',  // Connection aborted
];

/**
 * Common retryable HTTP status codes
 * 
 * These status codes typically indicate temporary server issues or rate limiting
 * that may be resolved by retrying the request after a delay:
 * - 408: Request Timeout
 * - 429: Too Many Requests (rate limiting)
 * - 500: Internal Server Error
 * - 502: Bad Gateway
 * - 503: Service Unavailable
 * - 504: Gateway Timeout
 */
export const RETRYABLE_STATUS_CODES = [408, 429, 500, 502, 503, 504];

/**
 * Error with additional properties for network and HTTP errors
 */
interface ExtendedError extends Error {
  code?: string;
  status?: number;
  statusCode?: number;
  errno?: number;
  syscall?: string;
  response?: { status?: number };
}

/**
 * Determines if an error is retryable based on its type or properties
 * 
 * This function examines various properties of the error to determine if the operation
 * that caused it should be retried. It checks error codes, status codes, and message
 * patterns that typically indicate temporary failures.
 * 
 * @param error - The error to check
 * @returns True if the error is retryable, false otherwise
 */
export function isRetryableError(error: Error): boolean {
  const extError = error as ExtendedError;
  
  // Check for network errors by error code
  if (extError.code && RETRYABLE_ERROR_TYPES.includes(extError.code)) {
    return true;
  }

  // Check for HTTP errors with retryable status codes (direct status property)
  if (extError.status && RETRYABLE_STATUS_CODES.includes(extError.status)) {
    return true;
  }
  
  // Check for HTTP errors with retryable status codes (statusCode property)
  if (extError.statusCode && RETRYABLE_STATUS_CODES.includes(extError.statusCode)) {
    return true;
  }
  
  // Check for HTTP errors in response object (for axios/fetch-like errors)
  if (extError.response?.status && RETRYABLE_STATUS_CODES.includes(extError.response.status)) {
    return true;
  }

  // Check for specific error messages that indicate temporary issues
  const errorMessage = error.message.toLowerCase();
  return (
    errorMessage.includes('timeout') ||
    errorMessage.includes('temporarily unavailable') ||
    errorMessage.includes('connection reset') ||
    errorMessage.includes('connection closed') ||
    errorMessage.includes('connection refused') ||
    errorMessage.includes('network error') ||
    errorMessage.includes('socket hang up') ||
    errorMessage.includes('eai_again') ||
    errorMessage.includes('too many requests') ||
    errorMessage.includes('rate limit') ||
    errorMessage.includes('server error') ||
    errorMessage.includes('service unavailable') ||
    errorMessage.includes('gateway timeout')
  );
}

/**
 * Calculates the delay for the next retry attempt with exponential backoff and jitter
 * 
 * @param attempt - The current retry attempt (1-based)
 * @param options - Retry configuration options
 * @returns The delay in milliseconds before the next retry
 */
export function calculateBackoffDelay(attempt: number, options: RetryOptions): number {
  // Calculate exponential backoff: initialDelay * (backoffFactor ^ attempt)
  const exponentialDelay = options.initialDelayMs * Math.pow(options.backoffFactor, attempt - 1);
  
  // Apply maximum delay constraint
  const cappedDelay = Math.min(exponentialDelay, options.maxDelayMs);
  
  // Apply jitter to prevent thundering herd problem
  // Formula: delay = baseDelay * (1 - jitterFactor/2 + jitterFactor * random)
  const jitterMultiplier = 1 - (options.jitterFactor / 2) + (options.jitterFactor * Math.random());
  
  // Return the final delay with jitter applied
  return Math.floor(cappedDelay * jitterMultiplier);
}

/**
 * Result of a retry operation, including metadata about the attempts
 */
export interface RetryResult<T> {
  /** The successful result of the operation */
  result: T;
  /** Number of attempts made (1 means success on first try) */
  attempts: number;
  /** Total time spent in retry delays (ms) */
  totalDelayMs: number;
  /** Whether the operation succeeded on the first attempt */
  succeededImmediately: boolean;
}

/**
 * Executes a function with retry logic using exponential backoff and jitter
 * 
 * @param fn - The async function to execute with retry logic
 * @param options - Retry configuration options
 * @returns A promise that resolves with the result of the function or rejects after all retries fail
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  options: Partial<RetryOptions> = {}
): Promise<T> {
  // Merge provided options with defaults
  const retryOptions: RetryOptions = {
    ...DEFAULT_RETRY_OPTIONS,
    ...options,
    isRetryable: options.isRetryable || isRetryableError,
  };

  let lastError: Error;
  let attempt = 0;
  let totalDelayMs = 0;

  while (attempt <= retryOptions.maxRetries) {
    try {
      // Attempt to execute the function
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      attempt++;

      // If we've exhausted all retry attempts, throw the last error
      if (attempt > retryOptions.maxRetries) {
        // Add retry metadata to the error for debugging
        (lastError as any).retryAttempts = attempt - 1;
        (lastError as any).totalDelayMs = totalDelayMs;
        throw lastError;
      }

      // Check if the error is retryable
      if (retryOptions.isRetryable && !retryOptions.isRetryable(lastError)) {
        // Add retry metadata to the error for debugging
        (lastError as any).retryAttempts = attempt - 1;
        (lastError as any).totalDelayMs = totalDelayMs;
        (lastError as any).notRetryable = true;
        throw lastError;
      }

      // Calculate delay for next retry
      const delay = calculateBackoffDelay(attempt, retryOptions);
      totalDelayMs += delay;

      // Execute onRetry callback if provided
      if (retryOptions.onRetry) {
        retryOptions.onRetry(lastError, attempt, delay);
      }

      // Wait for the calculated delay before retrying
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  // This should never be reached due to the throw in the loop,
  // but TypeScript requires a return statement
  throw lastError!;
}

/**
 * Executes a function with retry logic and returns detailed metadata about the operation
 * 
 * @param fn - The async function to execute with retry logic
 * @param options - Retry configuration options
 * @returns A promise that resolves with the result and retry metadata or rejects after all retries fail
 */
export async function withRetryDetailed<T>(
  fn: () => Promise<T>,
  options: Partial<RetryOptions> = {}
): Promise<RetryResult<T>> {
  // Merge provided options with defaults
  const retryOptions: RetryOptions = {
    ...DEFAULT_RETRY_OPTIONS,
    ...options,
    isRetryable: options.isRetryable || isRetryableError,
  };

  let attempt = 0;
  let totalDelayMs = 0;
  let lastError: Error;

  while (attempt <= retryOptions.maxRetries) {
    try {
      // Increment attempt counter (first attempt is 1)
      attempt++;
      
      // If this is the first attempt, execute immediately
      if (attempt === 1) {
        const result = await fn();
        return {
          result,
          attempts: 1,
          totalDelayMs: 0,
          succeededImmediately: true,
        };
      }
      
      // For retry attempts, execute after recording metadata
      const result = await fn();
      return {
        result,
        attempts: attempt,
        totalDelayMs,
        succeededImmediately: false,
      };
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      
      // If we've exhausted all retry attempts, throw the last error
      if (attempt >= retryOptions.maxRetries) {
        // Add retry metadata to the error for debugging
        (lastError as any).retryAttempts = attempt;
        (lastError as any).totalDelayMs = totalDelayMs;
        throw lastError;
      }

      // Check if the error is retryable
      if (retryOptions.isRetryable && !retryOptions.isRetryable(lastError)) {
        // Add retry metadata to the error for debugging
        (lastError as any).retryAttempts = attempt;
        (lastError as any).totalDelayMs = totalDelayMs;
        (lastError as any).notRetryable = true;
        throw lastError;
      }

      // Calculate delay for next retry
      const delay = calculateBackoffDelay(attempt, retryOptions);
      totalDelayMs += delay;

      // Execute onRetry callback if provided
      if (retryOptions.onRetry) {
        retryOptions.onRetry(lastError, attempt, delay);
      }

      // Wait for the calculated delay before retrying
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  // This should never be reached due to the throw in the loop,
  // but TypeScript requires a return statement
  throw lastError!;
}

/**
 * Creates a retryable version of an async function
 * 
 * This utility wraps an existing async function with retry logic, returning a new function
 * with the same signature that automatically retries on failure according to the specified options.
 * 
 * @param fn - The async function to make retryable
 * @param options - Retry configuration options
 * @returns A new function that wraps the original with retry logic
 * 
 * @example
 * ```typescript
 * // Original function
 * async function fetchUserData(userId: string): Promise<UserData> {
 *   const response = await fetch(`/api/users/${userId}`);
 *   if (!response.ok) throw new Error(`Failed to fetch user: ${response.status}`);
 *   return response.json();
 * }
 * 
 * // Create retryable version
 * const retryableFetchUserData = createRetryableFunction(fetchUserData, {
 *   maxRetries: 3,
 *   onRetry: (error, attempt) => console.log(`Retry ${attempt} after error: ${error.message}`)
 * });
 * 
 * // Use exactly like the original function
 * const userData = await retryableFetchUserData('user123');
 * ```
 */
export function createRetryableFunction<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  options: Partial<RetryOptions> = {}
): T {
  return ((...args: Parameters<T>): ReturnType<T> => {
    return withRetry(() => fn(...args), options) as ReturnType<T>;
  }) as T;
}

/**
 * Creates a retryable version of an async function with detailed retry information
 * 
 * Similar to createRetryableFunction, but the returned function provides detailed
 * information about the retry process, including number of attempts and total delay.
 * 
 * @param fn - The async function to make retryable
 * @param options - Retry configuration options
 * @returns A new function that wraps the original with retry logic and returns detailed results
 * 
 * @example
 * ```typescript
 * // Create detailed retryable version
 * const detailedFetchUserData = createDetailedRetryableFunction(fetchUserData);
 * 
 * // Get result with retry metadata
 * const { result: userData, attempts, totalDelayMs } = await detailedFetchUserData('user123');
 * console.log(`Fetched user data after ${attempts} attempts with ${totalDelayMs}ms total delay`);
 * ```
 */
export function createDetailedRetryableFunction<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  options: Partial<RetryOptions> = {}
): (...args: Parameters<T>) => Promise<RetryResult<Awaited<ReturnType<T>>>> {
  return (...args: Parameters<T>): Promise<RetryResult<Awaited<ReturnType<T>>>> => {
    return withRetryDetailed(() => fn(...args), options);
  };
}

/**
 * Utility for retrying a specific operation with custom options
 * 
 * This object provides a convenient API for the retry functionality:
 * 
 * Example usage:
 * ```typescript
 * // Simple retry with default options
 * const result = await retry.execute(async () => {
 *   return await fetchDataFromApi();
 * });
 * 
 * // Create a retryable version of a function
 * const retryableFetch = retry.create(fetchDataFromApi, { maxRetries: 5 });
 * const result = await retryableFetch();
 * 
 * // Custom retry with logging
 * const result = await retry.execute(
 *   async () => await connectToDatabase(),
 *   {
 *     maxRetries: 5,
 *     initialDelayMs: 2000,
 *     onRetry: (error, attempt, delay) => {
 *       logger.warn(`Database connection failed (attempt ${attempt}): ${error.message}. Retrying in ${delay}ms...`);
 *     }
 *   }
 * );
 * 
 * // Get detailed retry information
 * const { result, attempts, totalDelayMs } = await retry.executeDetailed(
 *   async () => await fetchDataFromApi()
 * );
 * ```
 */
export const retry = {
  /**
   * Executes a function with retry logic
   */
  execute: withRetry,
  
  /**
   * Executes a function with retry logic and returns detailed metadata
   */
  executeDetailed: withRetryDetailed,
  
  /**
   * Creates a retryable version of a function
   */
  create: createRetryableFunction,
  
  /**
   * Creates a retryable version of a function that returns detailed metadata
   */
  createDetailed: createDetailedRetryableFunction,
  
  /**
   * Checks if an error is retryable
   */
  isRetryable: isRetryableError,
  
  /**
   * Calculates backoff delay with jitter
   */
  calculateDelay: calculateBackoffDelay,
  
  /**
   * Predefined retry configurations
   */
  options: {
    default: DEFAULT_RETRY_OPTIONS,
    aggressive: AGGRESSIVE_RETRY_OPTIONS,
    conservative: CONSERVATIVE_RETRY_OPTIONS,
  },
};

export default retry;