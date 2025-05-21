"""Unit tests for retry_utils module.

This module contains tests for the retry logic utilities in the Document Service.
Tests verify that the retry mechanisms with exponential backoff, jitter, and 
configurable limits work correctly.
"""

import asyncio
import logging
import time
from unittest import mock

import pytest

# Fix module import path for tests
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

# Import the module directly for testing
from utils.retry_utils import (
    is_retryable_error,
    calculate_backoff_with_jitter,
    retry_with_backoff,
    async_retry_with_backoff,
    retry_rabbitmq_publish,
    async_retry_rabbitmq_publish,
    DEFAULT_MAX_RETRIES,
    DEFAULT_INITIAL_DELAY,
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_DELAY,
    DEFAULT_JITTER_FACTOR
)


# Import the full module for additional testing if needed
import utils.retry_utils as retry_utils_module


# Configure test logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Test fixtures
@pytest.fixture
def mock_time_sleep():
    """Mock time.sleep to speed up tests."""
    with mock.patch('time.sleep') as mock_sleep:
        yield mock_sleep


@pytest.fixture
def mock_asyncio_sleep():
    """Mock asyncio.sleep to speed up tests."""
    with mock.patch('asyncio.sleep') as mock_sleep:
        yield mock_sleep


@pytest.fixture
def mock_random():
    """Mock random.uniform to make tests deterministic."""
    with mock.patch('random.uniform', return_value=0.5) as mock_rand:
        yield mock_rand


# Tests for is_retryable_error
class TestIsRetryableError:
    """Tests for the is_retryable_error function."""

    def test_default_retryable_exceptions(self):
        """Test that default retryable exceptions are correctly identified."""
        # Default retryable exceptions include ConnectionError, TimeoutError, OSError
        assert is_retryable_error(ConnectionError())
        assert is_retryable_error(TimeoutError())
        assert is_retryable_error(OSError())
        
        # Non-retryable exceptions
        assert not is_retryable_error(ValueError())
        assert not is_retryable_error(TypeError())
        assert not is_retryable_error(KeyError())

    def test_custom_retryable_exceptions(self):
        """Test that custom retryable exceptions are correctly identified."""
        custom_exceptions = [ValueError, KeyError]
        
        # Should be retryable with custom list
        assert is_retryable_error(ValueError(), custom_exceptions)
        assert is_retryable_error(KeyError(), custom_exceptions)
        
        # Should not be retryable with custom list
        assert not is_retryable_error(TypeError(), custom_exceptions)
        assert not is_retryable_error(ConnectionError(), custom_exceptions)

    def test_subclass_exceptions(self):
        """Test that subclasses of retryable exceptions are correctly identified."""
        # Create a custom exception that inherits from a retryable exception
        class CustomConnectionError(ConnectionError):
            pass
        
        # Should be retryable as it's a subclass of ConnectionError
        assert is_retryable_error(CustomConnectionError())
        
        # Create a custom exception that doesn't inherit from a retryable exception
        class CustomError(Exception):
            pass
        
        # Should not be retryable
        assert not is_retryable_error(CustomError())


# Tests for calculate_backoff_with_jitter
class TestCalculateBackoffWithJitter:
    """Tests for the calculate_backoff_with_jitter function."""

    def test_no_jitter(self):
        """Test backoff calculation with no jitter."""
        # Test with default parameters
        backoff = calculate_backoff_with_jitter(
            retry_attempt=0,
            jitter_type='none'
        )
        assert backoff == DEFAULT_INITIAL_DELAY
        
        # Test with custom parameters
        backoff = calculate_backoff_with_jitter(
            retry_attempt=2,
            initial_delay=1.0,
            backoff_factor=2.0,
            jitter_type='none'
        )
        assert backoff == 4.0  # 1.0 * (2.0 ^ 2)

    def test_full_jitter(self, mock_random):
        """Test backoff calculation with full jitter."""
        # Test with default parameters and mocked random
        backoff = calculate_backoff_with_jitter(
            retry_attempt=1,
            jitter_type='full'
        )
        # With mocked random.uniform returning 0.5, and DEFAULT_INITIAL_DELAY=1.0, DEFAULT_BACKOFF_FACTOR=2.0
        # Expected: 0.5 * (1.0 * (2.0 ^ 1)) = 1.0
        assert backoff == 1.0
        mock_random.assert_called_once()

    def test_equal_jitter(self, mock_random):
        """Test backoff calculation with equal jitter."""
        # Test with custom parameters and mocked random
        backoff = calculate_backoff_with_jitter(
            retry_attempt=1,
            initial_delay=2.0,
            backoff_factor=3.0,
            jitter_type='equal'
        )
        # Base backoff: 2.0 * (3.0 ^ 1) = 6.0
        # With equal jitter and mocked random.uniform returning 0.5:
        # 6.0 - (6.0 * 0.5 * 0.5) + (0.5 * (6.0 * 0.5)) = 6.0 - 1.5 + 1.5 = 6.0
        assert backoff == 6.0

    def test_decorrelated_jitter(self, mock_random):
        """Test backoff calculation with decorrelated jitter."""
        # For decorrelated jitter, we use a simplified implementation
        # that doesn't require tracking previous values
        with mock.patch('random.uniform', return_value=3.0) as mock_rand:
            backoff = calculate_backoff_with_jitter(
                retry_attempt=1,
                initial_delay=1.0,
                backoff_factor=2.0,
                max_delay=10.0,
                jitter_type='decorrelated'
            )
            # With mocked random.uniform returning 3.0
            assert backoff == 3.0

    def test_max_delay(self):
        """Test that backoff doesn't exceed max_delay."""
        # Set up a scenario where the calculated backoff would exceed max_delay
        backoff = calculate_backoff_with_jitter(
            retry_attempt=10,  # Very high retry attempt
            initial_delay=1.0,
            backoff_factor=2.0,
            max_delay=30.0,
            jitter_type='none'
        )
        # 1.0 * (2.0 ^ 10) = 1024, which exceeds max_delay of 30.0
        assert backoff == 30.0

    def test_invalid_jitter_type(self, caplog):
        """Test behavior with invalid jitter type."""
        with caplog.at_level(logging.WARNING):
            backoff = calculate_backoff_with_jitter(
                retry_attempt=1,
                jitter_type='invalid_type'
            )
            # Should default to full jitter
            assert "Unknown jitter type 'invalid_type'" in caplog.text
            # With mocked random in conftest returning 0.5
            assert backoff == 1.0


# Tests for retry_with_backoff decorator
class TestRetryWithBackoff:
    """Tests for the retry_with_backoff decorator."""

    def test_successful_execution(self):
        """Test that a successful function execution doesn't trigger retries."""
        mock_func = mock.Mock(return_value="success")
        decorated_func = retry_with_backoff()(mock_func)
        
        result = decorated_func()
        
        assert result == "success"
        mock_func.assert_called_once()

    def test_retry_on_retryable_error(self, mock_time_sleep):
        """Test that retryable errors trigger retries."""
        # Mock function that fails with ConnectionError twice, then succeeds
        mock_func = mock.Mock(side_effect=[ConnectionError(), ConnectionError(), "success"])
        decorated_func = retry_with_backoff(max_retries=3)(mock_func)
        
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
        assert mock_time_sleep.call_count == 2

    def test_max_retries_exceeded(self, mock_time_sleep):
        """Test that exceeding max retries raises the last exception."""
        # Mock function that always fails with ConnectionError
        mock_func = mock.Mock(side_effect=ConnectionError("persistent error"))
        decorated_func = retry_with_backoff(max_retries=3)(mock_func)
        
        with pytest.raises(ConnectionError, match="persistent error"):
            decorated_func()
        
        assert mock_func.call_count == 4  # Initial attempt + 3 retries
        assert mock_time_sleep.call_count == 3

    def test_non_retryable_error(self, mock_time_sleep):
        """Test that non-retryable errors don't trigger retries."""
        # Mock function that fails with ValueError (non-retryable by default)
        mock_func = mock.Mock(side_effect=ValueError("non-retryable error"))
        decorated_func = retry_with_backoff(max_retries=3)(mock_func)
        
        with pytest.raises(ValueError, match="non-retryable error"):
            decorated_func()
        
        mock_func.assert_called_once()
        mock_time_sleep.assert_not_called()

    def test_custom_retryable_exceptions(self, mock_time_sleep):
        """Test retry with custom retryable exceptions."""
        # Mock function that fails with ValueError twice, then succeeds
        mock_func = mock.Mock(side_effect=[ValueError(), ValueError(), "success"])
        decorated_func = retry_with_backoff(
            max_retries=3,
            retryable_exceptions=[ValueError]
        )(mock_func)
        
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
        assert mock_time_sleep.call_count == 2

    def test_on_retry_callback(self, mock_time_sleep):
        """Test that on_retry callback is called before each retry."""
        # Create a mock callback
        mock_callback = mock.Mock()
        
        # Mock function that fails with ConnectionError twice, then succeeds
        mock_func = mock.Mock(side_effect=[ConnectionError(), ConnectionError(), "success"])
        decorated_func = retry_with_backoff(
            max_retries=3,
            on_retry=mock_callback
        )(mock_func)
        
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
        assert mock_callback.call_count == 2
        # Check that callback was called with the right arguments
        for i, call in enumerate(mock_callback.call_args_list):
            args, _ = call
            assert isinstance(args[0], ConnectionError)  # First arg is the exception
            assert args[1] == i + 1  # Second arg is the attempt number (1-based)


# Tests for async_retry_with_backoff decorator
class TestAsyncRetryWithBackoff:
    """Tests for the async_retry_with_backoff decorator."""

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Test that a successful async function execution doesn't trigger retries."""
        mock_func = mock.AsyncMock(return_value="success")
        decorated_func = async_retry_with_backoff()(mock_func)
        
        result = await decorated_func()
        
        assert result == "success"
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_on_retryable_error(self, mock_asyncio_sleep):
        """Test that retryable errors trigger retries in async functions."""
        # Mock async function that fails with ConnectionError twice, then succeeds
        mock_func = mock.AsyncMock(side_effect=[ConnectionError(), ConnectionError(), "success"])
        decorated_func = async_retry_with_backoff(max_retries=3)(mock_func)
        
        result = await decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
        assert mock_asyncio_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, mock_asyncio_sleep):
        """Test that exceeding max retries raises the last exception in async functions."""
        # Mock async function that always fails with ConnectionError
        mock_func = mock.AsyncMock(side_effect=ConnectionError("persistent error"))
        decorated_func = async_retry_with_backoff(max_retries=3)(mock_func)
        
        with pytest.raises(ConnectionError, match="persistent error"):
            await decorated_func()
        
        assert mock_func.call_count == 4  # Initial attempt + 3 retries
        assert mock_asyncio_sleep.call_count == 3

    @pytest.mark.asyncio
    async def test_non_retryable_error(self, mock_asyncio_sleep):
        """Test that non-retryable errors don't trigger retries in async functions."""
        # Mock async function that fails with ValueError (non-retryable by default)
        mock_func = mock.AsyncMock(side_effect=ValueError("non-retryable error"))
        decorated_func = async_retry_with_backoff(max_retries=3)(mock_func)
        
        with pytest.raises(ValueError, match="non-retryable error"):
            await decorated_func()
        
        mock_func.assert_called_once()
        mock_asyncio_sleep.assert_not_called()


# Tests for specialized RabbitMQ retry decorators
class TestRabbitMQRetryDecorators:
    """Tests for the specialized RabbitMQ retry decorators."""

    def test_retry_rabbitmq_publish(self, mock_time_sleep):
        """Test the retry_rabbitmq_publish decorator."""
        # Mock function that fails with ConnectionError twice, then succeeds
        mock_func = mock.Mock(side_effect=[ConnectionError(), ConnectionError(), "success"])
        decorated_func = retry_rabbitmq_publish()(mock_func)
        
        result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
        assert mock_time_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_async_retry_rabbitmq_publish(self, mock_asyncio_sleep):
        """Test the async_retry_rabbitmq_publish decorator."""
        # Mock async function that fails with ConnectionError twice, then succeeds
        mock_func = mock.AsyncMock(side_effect=[ConnectionError(), ConnectionError(), "success"])
        decorated_func = async_retry_rabbitmq_publish()(mock_func)
        
        result = await decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
        assert mock_asyncio_sleep.call_count == 2

    def test_rabbitmq_specific_parameters(self):
        """Test that RabbitMQ decorators use specific parameters."""
        # Use mock to inspect the decorator parameters
        with mock.patch('utils.retry_utils.retry_with_backoff') as mock_retry:
            retry_rabbitmq_publish()
            
            # Check that the decorator was called with RabbitMQ-specific parameters
            mock_retry.assert_called_once()
            _, kwargs = mock_retry.call_args
            assert kwargs['max_retries'] == 5
            assert kwargs['initial_delay'] == 0.5
            assert kwargs['backoff_factor'] == 2.0
            assert kwargs['max_delay'] == 30.0
            assert kwargs['jitter_type'] == 'full'
            # Check that the retryable exceptions include ConnectionError and TimeoutError
            retryable_exceptions = kwargs['retryable_exceptions']
            assert any(exc is ConnectionError for exc in retryable_exceptions)
            assert any(exc is TimeoutError for exc in retryable_exceptions)


# Integration tests with real functions
class TestIntegrationTests:
    """Integration tests with real functions (not mocks)."""

    def test_real_function_with_retry(self, mock_time_sleep):
        """Test a real function with the retry decorator."""
        # Counter to track number of calls
        call_count = {'value': 0}
        
        @retry_with_backoff(max_retries=2)
        def flaky_function():
            call_count['value'] += 1
            if call_count['value'] <= 2:
                raise ConnectionError("Simulated connection error")
            return "Success!"
        
        result = flaky_function()
        
        assert result == "Success!"
        assert call_count['value'] == 3
        assert mock_time_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_real_async_function_with_retry(self, mock_asyncio_sleep):
        """Test a real async function with the async retry decorator."""
        # Counter to track number of calls
        call_count = {'value': 0}
        
        @async_retry_with_backoff(max_retries=2)
        async def flaky_async_function():
            call_count['value'] += 1
            if call_count['value'] <= 2:
                raise TimeoutError("Simulated timeout error")
            return "Async Success!"
        
        result = await flaky_async_function()
        
        assert result == "Async Success!"
        assert call_count['value'] == 3
        assert mock_asyncio_sleep.call_count == 2


# Performance tests
class TestPerformance:
    """Performance tests for retry utilities."""

    def test_backoff_calculation_performance(self):
        """Test the performance of backoff calculation."""
        # Measure the time it takes to calculate backoff 1000 times
        start_time = time.time()
        for i in range(1000):
            calculate_backoff_with_jitter(i % 10)
        end_time = time.time()
        
        # Should be very fast (typically < 0.1s)
        execution_time = end_time - start_time
        logger.info(f"Backoff calculation performance: {execution_time:.6f}s for 1000 iterations")
        
        # This is a soft assertion - we're just logging the time
        # In a real test, you might want to assert that it's below a threshold
        assert execution_time < 1.0, "Backoff calculation should be fast"

    def test_is_retryable_error_performance(self):
        """Test the performance of error eligibility checking."""
        # Create a list of exceptions to check
        exceptions = [
            ConnectionError(),
            TimeoutError(),
            ValueError(),
            TypeError(),
            KeyError(),
            OSError()
        ]
        
        # Measure the time it takes to check 1000 exceptions
        start_time = time.time()
        for _ in range(1000):
            for exc in exceptions:
                is_retryable_error(exc)
        end_time = time.time()
        
        # Should be very fast (typically < 0.1s)
        execution_time = end_time - start_time
        logger.info(f"Error eligibility checking performance: {execution_time:.6f}s for 6000 checks")
        
        # This is a soft assertion - we're just logging the time
        assert execution_time < 1.0, "Error eligibility checking should be fast"