"""
Retry Utilities for OCR Service.

This module provides utility functions for implementing retry mechanisms with
exponential backoff, jitter, and configurable limits. These utilities are essential
for handling temporary failures in external service connections and ensuring reliable
operation of the OCR Service.
"""

import asyncio
import functools
import logging
import random
import time
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast

# Type variables for function signatures
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])
AsyncF = TypeVar('AsyncF', bound=Callable[..., Any])

# Configure logger
logger = logging.getLogger(__name__)

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_BACKOFF = 1.0  # seconds
DEFAULT_MAX_BACKOFF = 60.0  # seconds
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_JITTER_FACTOR = 0.1  # 10% jitter

# Default retryable exceptions for S3 and other common services
# Note: Import actual S3 exceptions when using the AWS SDK
try:
    from botocore.exceptions import ClientError, ConnectionError as BotoCoreConnectionError, \
        ConnectTimeoutError, ReadTimeoutError, EndpointConnectionError, \
        HTTPClientError, IncompleteReadError, ResponseStreamingError, \
        OperationNotPageableError, NoCredentialsError, PartialCredentialsError
    
    # S3-specific exceptions that are typically retryable
    DEFAULT_RETRYABLE_EXCEPTIONS = (
        ConnectionError,
        TimeoutError,
        BotoCoreConnectionError,
        ConnectTimeoutError,
        ReadTimeoutError,
        EndpointConnectionError,
        HTTPClientError,
        IncompleteReadError,
        # Include specific ClientError cases that are retryable
    )
    
    # S3 error codes that are typically retryable
    # Based on AWS documentation and boto3 retry behavior
    RETRYABLE_S3_ERROR_CODES = {
        # Transient errors/exceptions
        'RequestTimeout',
        'RequestTimeoutException',
        'PriorRequestNotComplete',
        'ConnectionError',
        'InternalError',
        'ServiceUnavailable',
        
        # Service-side throttling/limit errors
        'ThrottlingException',
        'Throttling',
        'TooManyRequestsException',
        'ProvisionedThroughputExceededException',
        'RequestLimitExceeded',
        'BandwidthLimitExceeded',
        'RequestThrottled',
        'SlowDown',
        'TransactionInProgressException',
        'EC2ThrottledException',
        'LimitExceededException',
        
        # HTTP status codes
        '500',  # Internal Server Error
        '502',  # Bad Gateway
        '503',  # Service Unavailable
        '504',  # Gateway Timeout
    }
    
    # S3 error codes that should NOT be retried
    NON_RETRYABLE_S3_ERROR_CODES = {
        'NoSuchKey',
        'NoSuchBucket',
        'InvalidRequest',
        'InvalidArgument',
        'AccessDenied',
        'AuthorizationHeaderMalformed',
        'ExpiredToken',
        'SignatureDoesNotMatch',
        '400',  # Bad Request
        '401',  # Unauthorized
        '403',  # Forbidden
        '404',  # Not Found
        '405',  # Method Not Allowed
    }
    
    HAS_BOTO3 = True
except ImportError:
    # Fallback if boto3/botocore is not installed
    DEFAULT_RETRYABLE_EXCEPTIONS = (
        ConnectionError,
        TimeoutError,
    )
    RETRYABLE_S3_ERROR_CODES = set()
    NON_RETRYABLE_S3_ERROR_CODES = set()
    HAS_BOTO3 = False


def is_retryable_exception(exception: Exception) -> bool:
    """
    Determine if an exception is retryable based on its type and attributes.
    
    Args:
        exception: The exception to check
        
    Returns:
        bool: True if the exception is retryable, False otherwise
    """
    # Check if exception is an instance of known retryable exceptions
    if isinstance(exception, DEFAULT_RETRYABLE_EXCEPTIONS):
        return True
    
    # Check for boto3/botocore ClientError with retryable error code
    if HAS_BOTO3 and isinstance(exception, ClientError):
        error_code = exception.response.get('Error', {}).get('Code', '')
        status_code = str(exception.response.get('ResponseMetadata', {}).get('HTTPStatusCode', ''))
        
        return (error_code in RETRYABLE_S3_ERROR_CODES or 
                status_code in RETRYABLE_S3_ERROR_CODES)
    
    # Check for HTTP status code in exception (for requests library and similar)
    if hasattr(exception, 'status_code'):
        return str(getattr(exception, 'status_code')) in {'500', '502', '503', '504'}
    
    return False


def calculate_backoff(attempt: int, 
                     initial_backoff: float = DEFAULT_INITIAL_BACKOFF,
                     max_backoff: float = DEFAULT_MAX_BACKOFF,
                     backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
                     jitter_factor: float = DEFAULT_JITTER_FACTOR) -> float:
    """
    Calculate the backoff time for a retry attempt with exponential backoff and jitter.
    
    Args:
        attempt: The current retry attempt (0-based)
        initial_backoff: The initial backoff time in seconds
        max_backoff: The maximum backoff time in seconds
        backoff_factor: The multiplier for exponential backoff
        jitter_factor: The factor for random jitter (0.0 to 1.0)
        
    Returns:
        float: The calculated backoff time in seconds
    """
    # Calculate exponential backoff
    backoff = min(initial_backoff * (backoff_factor ** attempt), max_backoff)
    
    # Apply jitter to prevent thundering herd problem
    jitter_range = backoff * jitter_factor
    jitter = random.uniform(-jitter_range, jitter_range)
    
    # Ensure backoff is never negative due to jitter
    return max(0.001, backoff + jitter)


def retry(max_retries: int = DEFAULT_MAX_RETRIES,
          initial_backoff: float = DEFAULT_INITIAL_BACKOFF,
          max_backoff: float = DEFAULT_MAX_BACKOFF,
          backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
          jitter_factor: float = DEFAULT_JITTER_FACTOR,
          retryable_exceptions: Optional[tuple] = None,
          retry_on_result: Optional[Callable[[Any], bool]] = None) -> Callable[[F], F]:
    """
    Decorator for retrying a function if it raises specified exceptions or returns a result
    that satisfies the retry_on_result predicate.
    
    Args:
        max_retries: Maximum number of retries
        initial_backoff: Initial backoff time in seconds
        max_backoff: Maximum backoff time in seconds
        backoff_factor: Multiplier for exponential backoff
        jitter_factor: Factor for random jitter (0.0 to 1.0)
        retryable_exceptions: Tuple of exceptions that trigger a retry
        retry_on_result: Function that takes the result and returns True if retry is needed
        
    Returns:
        Callable: Decorated function with retry logic
    """
    retryable_excs = retryable_exceptions or DEFAULT_RETRYABLE_EXCEPTIONS
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):  # +1 for the initial attempt
                try:
                    result = func(*args, **kwargs)
                    
                    # Check if we should retry based on the result
                    if retry_on_result and retry_on_result(result):
                        if attempt < max_retries:
                            backoff_time = calculate_backoff(
                                attempt, initial_backoff, max_backoff, 
                                backoff_factor, jitter_factor
                            )
                            
                            logger.info(
                                f"Retrying {func.__name__} in {backoff_time:.2f}s due to result condition "
                                f"(attempt {attempt + 1}/{max_retries})"
                            )
                            
                            time.sleep(backoff_time)
                            continue
                    
                    return result
                    
                except retryable_excs as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        backoff_time = calculate_backoff(
                            attempt, initial_backoff, max_backoff, 
                            backoff_factor, jitter_factor
                        )
                        
                        logger.warning(
                            f"Retrying {func.__name__} in {backoff_time:.2f}s due to {e.__class__.__name__}: {e} "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        
                        time.sleep(backoff_time)
                    else:
                        logger.error(
                            f"Failed to execute {func.__name__} after {max_retries} retries: "
                            f"{last_exception.__class__.__name__}: {last_exception}"
                        )
                        raise
                except Exception as e:
                    # Non-retryable exception, check if it's actually retryable
                    if is_retryable_exception(e) and attempt < max_retries:
                        last_exception = e
                        backoff_time = calculate_backoff(
                            attempt, initial_backoff, max_backoff, 
                            backoff_factor, jitter_factor
                        )
                        
                        logger.warning(
                            f"Retrying {func.__name__} in {backoff_time:.2f}s due to {e.__class__.__name__}: {e} "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        
                        time.sleep(backoff_time)
                    else:
                        # Non-retryable exception, re-raise immediately
                        raise
            
            # This should never be reached due to the raise in the last iteration
            # But just in case, re-raise the last exception
            if last_exception:
                raise last_exception
            
            # If we somehow got here without a result or exception, raise RuntimeError
            raise RuntimeError(f"Unexpected state in retry decorator for {func.__name__}")
        
        return cast(F, wrapper)
    
    return decorator


async def async_sleep(seconds: float) -> None:
    """
    Asynchronous sleep function.
    
    Args:
        seconds: Time to sleep in seconds
    """
    await asyncio.sleep(seconds)


def async_retry(max_retries: int = DEFAULT_MAX_RETRIES,
                initial_backoff: float = DEFAULT_INITIAL_BACKOFF,
                max_backoff: float = DEFAULT_MAX_BACKOFF,
                backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
                jitter_factor: float = DEFAULT_JITTER_FACTOR,
                retryable_exceptions: Optional[tuple] = None,
                retry_on_result: Optional[Callable[[Any], bool]] = None) -> Callable[[AsyncF], AsyncF]:
    """
    Decorator for retrying an async function if it raises specified exceptions or returns a result
    that satisfies the retry_on_result predicate.
    
    Args:
        max_retries: Maximum number of retries
        initial_backoff: Initial backoff time in seconds
        max_backoff: Maximum backoff time in seconds
        backoff_factor: Multiplier for exponential backoff
        jitter_factor: Factor for random jitter (0.0 to 1.0)
        retryable_exceptions: Tuple of exceptions that trigger a retry
        retry_on_result: Function that takes the result and returns True if retry is needed
        
    Returns:
        Callable: Decorated async function with retry logic
    """
    retryable_excs = retryable_exceptions or DEFAULT_RETRYABLE_EXCEPTIONS
    
    def decorator(func: AsyncF) -> AsyncF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):  # +1 for the initial attempt
                try:
                    result = await func(*args, **kwargs)
                    
                    # Check if we should retry based on the result
                    if retry_on_result and retry_on_result(result):
                        if attempt < max_retries:
                            backoff_time = calculate_backoff(
                                attempt, initial_backoff, max_backoff, 
                                backoff_factor, jitter_factor
                            )
                            
                            logger.info(
                                f"Retrying {func.__name__} in {backoff_time:.2f}s due to result condition "
                                f"(attempt {attempt + 1}/{max_retries})"
                            )
                            
                            await async_sleep(backoff_time)
                            continue
                    
                    return result
                    
                except retryable_excs as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        backoff_time = calculate_backoff(
                            attempt, initial_backoff, max_backoff, 
                            backoff_factor, jitter_factor
                        )
                        
                        logger.warning(
                            f"Retrying {func.__name__} in {backoff_time:.2f}s due to {e.__class__.__name__}: {e} "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        
                        await async_sleep(backoff_time)
                    else:
                        logger.error(
                            f"Failed to execute {func.__name__} after {max_retries} retries: "
                            f"{last_exception.__class__.__name__}: {last_exception}"
                        )
                        raise
                except Exception as e:
                    # Non-retryable exception, check if it's actually retryable
                    if is_retryable_exception(e) and attempt < max_retries:
                        last_exception = e
                        backoff_time = calculate_backoff(
                            attempt, initial_backoff, max_backoff, 
                            backoff_factor, jitter_factor
                        )
                        
                        logger.warning(
                            f"Retrying {func.__name__} in {backoff_time:.2f}s due to {e.__class__.__name__}: {e} "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        
                        await async_sleep(backoff_time)
                    else:
                        # Non-retryable exception, re-raise immediately
                        raise
            
            # This should never be reached due to the raise in the last iteration
            # But just in case, re-raise the last exception
            if last_exception:
                raise last_exception
            
            # If we somehow got here without a result or exception, raise RuntimeError
            raise RuntimeError(f"Unexpected state in async_retry decorator for {func.__name__}")
        
        return cast(AsyncF, wrapper)
    
    return decorator


# Specialized retry functions for common OCR service operations

def retry_s3_operation(func: F, max_retries: int = 5) -> F:
    """
    Specialized retry decorator for S3 operations with appropriate settings.
    
    Args:
        func: The function to decorate
        max_retries: Maximum number of retries (default is higher for S3 operations)
        
    Returns:
        Callable: Decorated function with S3-specific retry logic
    """
    return retry(
        max_retries=max_retries,
        initial_backoff=1.0,
        max_backoff=30.0,
        backoff_factor=2.0,
        jitter_factor=0.2  # Higher jitter for distributed systems
    )(func)


def async_retry_s3_operation(func: AsyncF, max_retries: int = 5) -> AsyncF:
    """
    Specialized async retry decorator for S3 operations with appropriate settings.
    
    Args:
        func: The async function to decorate
        max_retries: Maximum number of retries (default is higher for S3 operations)
        
    Returns:
        Callable: Decorated async function with S3-specific retry logic
    """
    return async_retry(
        max_retries=max_retries,
        initial_backoff=1.0,
        max_backoff=30.0,
        backoff_factor=2.0,
        jitter_factor=0.2  # Higher jitter for distributed systems
    )(func)


def retry_rabbitmq_operation(func: F, max_retries: int = 3) -> F:
    """
    Specialized retry decorator for RabbitMQ operations.
    
    Args:
        func: The function to decorate
        max_retries: Maximum number of retries
        
    Returns:
        Callable: Decorated function with RabbitMQ-specific retry logic
    """
    return retry(
        max_retries=max_retries,
        initial_backoff=0.5,  # Start with a shorter backoff for messaging
        max_backoff=10.0,
        backoff_factor=2.0,
        jitter_factor=0.1
    )(func)


def async_retry_rabbitmq_operation(func: AsyncF, max_retries: int = 3) -> AsyncF:
    """
    Specialized async retry decorator for RabbitMQ operations.
    
    Args:
        func: The async function to decorate
        max_retries: Maximum number of retries
        
    Returns:
        Callable: Decorated async function with RabbitMQ-specific retry logic
    """
    return async_retry(
        max_retries=max_retries,
        initial_backoff=0.5,  # Start with a shorter backoff for messaging
        max_backoff=10.0,
        backoff_factor=2.0,
        jitter_factor=0.1
    )(func)


def is_s3_not_found_error(exception: Exception) -> bool:
    """
    Check if an exception is an S3 "not found" error that should not be retried.
    
    Args:
        exception: The exception to check
        
    Returns:
        bool: True if the exception is an S3 "not found" error, False otherwise
    """
    if HAS_BOTO3 and isinstance(exception, ClientError):
        error_code = exception.response.get('Error', {}).get('Code', '')
        return error_code in {'NoSuchKey', 'NoSuchBucket', '404'}
    
    # For non-boto exceptions that might indicate a not found error
    if hasattr(exception, 'status_code') and getattr(exception, 'status_code') == 404:
        return True
    
    return False


# Example usage

def retry_with_custom_condition(result: Any) -> bool:
    """
    Example custom condition for retry_on_result parameter.
    Retries if the result is None or an empty dict/list.
    
    Args:
        result: The result to check
        
    Returns:
        bool: True if retry is needed, False otherwise
    """
    if result is None:
        return True
    
    if isinstance(result, dict) and not result:
        return True
    
    if isinstance(result, list) and not result:
        return True
    
    return False


# Usage examples (commented out)

'''
# Example 1: Basic retry with default settings
@retry()
def fetch_document(document_id: str) -> dict:
    # Implementation
    pass

# Example 2: Async retry with custom settings
@async_retry(max_retries=5, initial_backoff=2.0)
async def process_document(document_id: str) -> dict:
    # Implementation
    pass

# Example 3: S3-specific retry
@retry_s3_operation
def download_document(bucket: str, key: str) -> bytes:
    # Implementation
    pass

# Example 4: Retry with custom result condition
@retry(retry_on_result=retry_with_custom_condition)
def extract_text(document: bytes) -> dict:
    # Implementation
    pass
'''