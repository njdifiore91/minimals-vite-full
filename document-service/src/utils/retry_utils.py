"""Retry Utilities for Document Service.

This module provides utility functions and decorators for implementing retry logic
with exponential backoff and jitter. It's designed to handle temporary failures
in external service connections and ensure reliable operation.

Typical usage:
    @retry_with_backoff(max_retries=5, initial_delay=1, backoff_factor=2)
    def function_that_might_fail():
        # Function implementation

    @async_retry_with_backoff(max_retries=3, initial_delay=0.5, backoff_factor=2)
    async def async_function_that_might_fail():
        # Async function implementation
"""

import asyncio
import functools
import logging
import random
import time
from typing import Any, Callable, List, Optional, Type, TypeVar, Union

# Type variables for function return types
T = TypeVar('T')  # Return type for synchronous functions
AT = TypeVar('AT')  # Return type for asynchronous functions

# Configure logger
logger = logging.getLogger(__name__)

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_DELAY = 1.0  # seconds
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_MAX_DELAY = 60.0  # seconds
DEFAULT_JITTER_FACTOR = 1.0  # full jitter


def is_retryable_error(exception: Exception, retryable_exceptions: List[Type[Exception]] = None) -> bool:
    """Determine if an exception is eligible for retry.
    
    Args:
        exception: The exception to check
        retryable_exceptions: List of exception types that are retryable
        
    Returns:
        bool: True if the exception is retryable, False otherwise
    """
    # If no specific exceptions are provided, use a default list
    if retryable_exceptions is None:
        # Common network and temporary failures
        retryable_exceptions = [
            ConnectionError,
            TimeoutError,
            OSError,  # Covers many I/O related errors
        ]
    
    # Check if the exception is an instance of any retryable exception
    return any(isinstance(exception, exc_type) for exc_type in retryable_exceptions)


def calculate_backoff_with_jitter(
    retry_attempt: int,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    max_delay: float = DEFAULT_MAX_DELAY,
    jitter_type: str = 'full',
    jitter_factor: float = DEFAULT_JITTER_FACTOR
) -> float:
    """Calculate backoff time with jitter.
    
    Args:
        retry_attempt: The current retry attempt (0-based)
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for exponential backoff
        max_delay: Maximum delay in seconds
        jitter_type: Type of jitter to apply ('full', 'equal', 'decorrelated', or 'none')
        jitter_factor: Factor to control jitter amount (0.0 to 1.0)
        
    Returns:
        float: The calculated backoff time in seconds
    """
    # Calculate base exponential backoff
    backoff = min(initial_delay * (backoff_factor ** retry_attempt), max_delay)
    
    # Apply jitter based on the specified type
    if jitter_type == 'none':
        return backoff
    
    elif jitter_type == 'full':
        # Full jitter: completely randomize between 0 and backoff
        return random.uniform(0, backoff * jitter_factor)
    
    elif jitter_type == 'equal':
        # Equal jitter: keep half of backoff, randomize the other half
        jitter_amount = backoff * 0.5 * jitter_factor
        return backoff - jitter_amount + random.uniform(0, jitter_amount * 2)
    
    elif jitter_type == 'decorrelated':
        # Decorrelated jitter: increases jitter based on previous value
        # For simplicity, we'll use a variation that doesn't require tracking previous values
        return min(max_delay, random.uniform(initial_delay, backoff * 3))
    
    else:
        # Default to full jitter if an invalid type is specified
        logger.warning(f"Unknown jitter type '{jitter_type}', using 'full' jitter instead")
        return random.uniform(0, backoff * jitter_factor)


def retry_with_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    max_delay: float = DEFAULT_MAX_DELAY,
    jitter_type: str = 'full',
    jitter_factor: float = DEFAULT_JITTER_FACTOR,
    retryable_exceptions: List[Type[Exception]] = None,
    on_retry: Callable[[Exception, int, float], None] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retrying functions with exponential backoff and jitter.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for exponential backoff
        max_delay: Maximum delay in seconds
        jitter_type: Type of jitter to apply ('full', 'equal', 'decorrelated', or 'none')
        jitter_factor: Factor to control jitter amount (0.0 to 1.0)
        retryable_exceptions: List of exception types that are retryable
        on_retry: Optional callback function called before each retry
        
    Returns:
        Callable: Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    
                    # Check if we've exceeded max retries or if the error is not retryable
                    if (attempt > max_retries or 
                            not is_retryable_error(e, retryable_exceptions)):
                        logger.error(
                            f"Failed after {attempt} attempts: {func.__name__}. Error: {str(e)}")
                        raise
                    
                    # Calculate backoff time with jitter
                    backoff_time = calculate_backoff_with_jitter(
                        attempt - 1,  # 0-based for calculation
                        initial_delay,
                        backoff_factor,
                        max_delay,
                        jitter_type,
                        jitter_factor
                    )
                    
                    # Log retry information
                    logger.warning(
                        f"Retry {attempt}/{max_retries} for {func.__name__} after {backoff_time:.2f}s. "
                        f"Error: {str(e)}")
                    
                    # Call on_retry callback if provided
                    if on_retry:
                        on_retry(e, attempt, backoff_time)
                    
                    # Wait before retrying
                    time.sleep(backoff_time)
        
        return wrapper
    
    return decorator


def async_retry_with_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    max_delay: float = DEFAULT_MAX_DELAY,
    jitter_type: str = 'full',
    jitter_factor: float = DEFAULT_JITTER_FACTOR,
    retryable_exceptions: List[Type[Exception]] = None,
    on_retry: Callable[[Exception, int, float], None] = None
) -> Callable[[Callable[..., AT]], Callable[..., AT]]:
    """Decorator for retrying async functions with exponential backoff and jitter.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for exponential backoff
        max_delay: Maximum delay in seconds
        jitter_type: Type of jitter to apply ('full', 'equal', 'decorrelated', or 'none')
        jitter_factor: Factor to control jitter amount (0.0 to 1.0)
        retryable_exceptions: List of exception types that are retryable
        on_retry: Optional callback function called before each retry
        
    Returns:
        Callable: Decorated async function with retry logic
    """
    def decorator(func: Callable[..., AT]) -> Callable[..., AT]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> AT:
            attempt = 0
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    
                    # Check if we've exceeded max retries or if the error is not retryable
                    if (attempt > max_retries or 
                            not is_retryable_error(e, retryable_exceptions)):
                        logger.error(
                            f"Failed after {attempt} attempts: {func.__name__}. Error: {str(e)}")
                        raise
                    
                    # Calculate backoff time with jitter
                    backoff_time = calculate_backoff_with_jitter(
                        attempt - 1,  # 0-based for calculation
                        initial_delay,
                        backoff_factor,
                        max_delay,
                        jitter_type,
                        jitter_factor
                    )
                    
                    # Log retry information
                    logger.warning(
                        f"Retry {attempt}/{max_retries} for {func.__name__} after {backoff_time:.2f}s. "
                        f"Error: {str(e)}")
                    
                    # Call on_retry callback if provided
                    if on_retry:
                        on_retry(e, attempt, backoff_time)
                    
                    # Wait before retrying
                    await asyncio.sleep(backoff_time)
        
        return wrapper
    
    return decorator


def retry_rabbitmq_publish(
    max_retries: int = 5,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    max_delay: float = 30.0,
    jitter_type: str = 'full'
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Specialized decorator for retrying RabbitMQ publish operations.
    
    This decorator is specifically designed for RabbitMQ publish operations,
    with optimized parameters and handling of RabbitMQ-specific exceptions.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for exponential backoff
        max_delay: Maximum delay in seconds
        jitter_type: Type of jitter to apply ('full', 'equal', 'decorrelated', or 'none')
        
    Returns:
        Callable: Decorated function with retry logic for RabbitMQ operations
    """
    # Import here to avoid circular imports
    # These are common RabbitMQ exceptions that should be retried
    rabbitmq_retryable_exceptions = [
        ConnectionError,
        TimeoutError,
        # Add specific RabbitMQ exceptions if using pika or other libraries
        # e.g., pika.exceptions.AMQPConnectionError
    ]
    
    return retry_with_backoff(
        max_retries=max_retries,
        initial_delay=initial_delay,
        backoff_factor=backoff_factor,
        max_delay=max_delay,
        jitter_type=jitter_type,
        retryable_exceptions=rabbitmq_retryable_exceptions
    )


def async_retry_rabbitmq_publish(
    max_retries: int = 5,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    max_delay: float = 30.0,
    jitter_type: str = 'full'
) -> Callable[[Callable[..., AT]], Callable[..., AT]]:
    """Specialized decorator for retrying async RabbitMQ publish operations.
    
    This decorator is specifically designed for async RabbitMQ publish operations,
    with optimized parameters and handling of RabbitMQ-specific exceptions.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for exponential backoff
        max_delay: Maximum delay in seconds
        jitter_type: Type of jitter to apply ('full', 'equal', 'decorrelated', or 'none')
        
    Returns:
        Callable: Decorated async function with retry logic for RabbitMQ operations
    """
    # Import here to avoid circular imports
    # These are common RabbitMQ exceptions that should be retried
    rabbitmq_retryable_exceptions = [
        ConnectionError,
        TimeoutError,
        # Add specific RabbitMQ exceptions if using pika or other libraries
        # e.g., pika.exceptions.AMQPConnectionError
    ]
    
    return async_retry_with_backoff(
        max_retries=max_retries,
        initial_delay=initial_delay,
        backoff_factor=backoff_factor,
        max_delay=max_delay,
        jitter_type=jitter_type,
        retryable_exceptions=rabbitmq_retryable_exceptions
    )


# Example usage
if __name__ == "__main__":
    # Example of a function with retry
    @retry_with_backoff(max_retries=3, initial_delay=1, backoff_factor=2)
    def example_function():
        # Simulate a failure
        if random.random() < 0.7:
            raise ConnectionError("Simulated connection error")
        return "Success!"
    
    # Example of an async function with retry
    @async_retry_with_backoff(max_retries=3, initial_delay=1, backoff_factor=2)
    async def example_async_function():
        # Simulate a failure
        if random.random() < 0.7:
            raise TimeoutError("Simulated timeout error")
        return "Async Success!"
    
    # Example of RabbitMQ publish with retry
    @retry_rabbitmq_publish()
    def publish_to_rabbitmq(message):
        # Actual implementation would use RabbitMQ client
        if random.random() < 0.5:
            raise ConnectionError("Simulated RabbitMQ connection error")
        print(f"Published message: {message}")
        return True