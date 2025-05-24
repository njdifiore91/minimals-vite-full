"""Unit tests for retry_utils module.

This module contains tests for the retry utilities in the Document Service,
including exponential backoff, jitter, and retry decorators for both
synchronous and asynchronous functions.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import random
import time

# Import the module to test
from src.utils.retry_utils import (
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


class TestIsRetryableError(unittest.TestCase):
    """Tests for the is_retryable_error function."""

    def test_default_retryable_exceptions(self):
        """Test that default retryable exceptions are correctly identified."""
        # Default retryable exceptions include ConnectionError, TimeoutError, OSError
        self.assertTrue(is_retryable_error(ConnectionError("Connection refused")))
        self.assertTrue(is_retryable_error(TimeoutError("Request timed out")))
        self.assertTrue(is_retryable_error(OSError("I/O error")))
        
        # Non-retryable exceptions
        self.assertFalse(is_retryable_error(ValueError("Invalid value")))
        self.assertFalse(is_retryable_error(KeyError("Missing key")))
        self.assertFalse(is_retryable_error(TypeError("Invalid type")))

    def test_custom_retryable_exceptions(self):
        """Test that custom retryable exceptions are correctly identified."""
        # Define custom retryable exceptions
        custom_exceptions = [ValueError, KeyError]
        
        # Should be retryable with custom list
        self.assertTrue(is_retryable_error(ValueError("Invalid value"), custom_exceptions))
        self.assertTrue(is_retryable_error(KeyError("Missing key"), custom_exceptions))
        
        # Should not be retryable with custom list
        self.assertFalse(is_retryable_error(TypeError("Invalid type"), custom_exceptions))
        self.assertFalse(is_retryable_error(ConnectionError("Connection refused"), custom_exceptions))

    def test_subclass_exceptions(self):
        """Test that subclasses of retryable exceptions are correctly identified."""
        # Create a custom exception that inherits from a retryable exception
        class CustomConnectionError(ConnectionError):
            pass
        
        # Should be retryable as it's a subclass of ConnectionError
        self.assertTrue(is_retryable_error(CustomConnectionError("Custom connection error")))


class TestCalculateBackoffWithJitter(unittest.TestCase):
    """Tests for the calculate_backoff_with_jitter function."""

    def setUp(self):
        # Set random seed for reproducible tests
        random.seed(42)

    def test_exponential_backoff_calculation(self):
        """Test that exponential backoff is calculated correctly without jitter."""
        # Test with default parameters but no jitter
        backoff_0 = calculate_backoff_with_jitter(0, jitter_type='none')
        backoff_1 = calculate_backoff_with_jitter(1, jitter_type='none')
        backoff_2 = calculate_backoff_with_jitter(2, jitter_type='none')
        
        # Verify exponential growth: initial_delay * (backoff_factor ^ retry_attempt)
        self.assertEqual(backoff_0, DEFAULT_INITIAL_DELAY)  # 1.0
        self.assertEqual(backoff_1, DEFAULT_INITIAL_DELAY * DEFAULT_BACKOFF_FACTOR)  # 1.0 * 2.0 = 2.0
        self.assertEqual(backoff_2, DEFAULT_INITIAL_DELAY * (DEFAULT_BACKOFF_FACTOR ** 2))  # 1.0 * (2.0^2) = 4.0

    def test_max_delay_limit(self):
        """Test that backoff is limited by max_delay."""
        # Set parameters to reach max_delay quickly
        initial_delay = 10.0
        backoff_factor = 3.0
        max_delay = 50.0
        
        # First retry: 10 * (3^0) = 10
        backoff_0 = calculate_backoff_with_jitter(
            0, initial_delay, backoff_factor, max_delay, jitter_type='none')
        self.assertEqual(backoff_0, 10.0)
        
        # Second retry: 10 * (3^1) = 30
        backoff_1 = calculate_backoff_with_jitter(
            1, initial_delay, backoff_factor, max_delay, jitter_type='none')
        self.assertEqual(backoff_1, 30.0)
        
        # Third retry: 10 * (3^2) = 90, but limited to max_delay = 50
        backoff_2 = calculate_backoff_with_jitter(
            2, initial_delay, backoff_factor, max_delay, jitter_type='none')
        self.assertEqual(backoff_2, 50.0)

    def test_full_jitter(self):
        """Test that full jitter produces values between 0 and calculated backoff."""
        # Use fixed parameters for testing
        initial_delay = 10.0
        backoff_factor = 2.0
        jitter_factor = 1.0
        
        # Calculate base backoff without jitter
        base_backoff = 10.0  # initial_delay * (backoff_factor^0)
        
        # Calculate with full jitter
        jittered_backoff = calculate_backoff_with_jitter(
            0, initial_delay, backoff_factor, DEFAULT_MAX_DELAY, 'full', jitter_factor)
        
        # With full jitter, result should be between 0 and base_backoff
        self.assertGreaterEqual(jittered_backoff, 0.0)
        self.assertLessEqual(jittered_backoff, base_backoff)
        
        # Verify it's not equal to base_backoff (jitter was applied)
        self.assertNotEqual(jittered_backoff, base_backoff)

    def test_equal_jitter(self):
        """Test that equal jitter produces values around the calculated backoff."""
        # Use fixed parameters for testing
        initial_delay = 10.0
        backoff_factor = 2.0
        
        # Calculate base backoff without jitter
        base_backoff = 10.0  # initial_delay * (backoff_factor^0)
        
        # Calculate with equal jitter
        jittered_backoff = calculate_backoff_with_jitter(
            0, initial_delay, backoff_factor, DEFAULT_MAX_DELAY, 'equal')
        
        # With equal jitter, result should be between base_backoff/2 and base_backoff*1.5
        self.assertGreaterEqual(jittered_backoff, base_backoff/2)
        self.assertLessEqual(jittered_backoff, base_backoff*1.5)

    def test_decorrelated_jitter(self):
        """Test that decorrelated jitter produces values within expected range."""
        # Use fixed parameters for testing
        initial_delay = 10.0
        backoff_factor = 2.0
        max_delay = 100.0
        
        # Calculate with decorrelated jitter
        jittered_backoff = calculate_backoff_with_jitter(
            0, initial_delay, backoff_factor, max_delay, 'decorrelated')
        
        # With decorrelated jitter, result should be between initial_delay and min(max_delay, base_backoff*3)
        self.assertGreaterEqual(jittered_backoff, initial_delay)
        self.assertLessEqual(jittered_backoff, min(max_delay, 10.0*3))

    def test_jitter_factor(self):
        """Test that jitter factor controls the amount of jitter applied."""
        # Use fixed parameters for testing
        initial_delay = 10.0
        jitter_factor = 0.5  # 50% jitter
        
        # Calculate with full jitter and reduced jitter factor
        jittered_backoff = calculate_backoff_with_jitter(
            0, initial_delay, DEFAULT_BACKOFF_FACTOR, DEFAULT_MAX_DELAY, 'full', jitter_factor)
        
        # With 50% jitter factor, result should be between 0 and base_backoff*0.5
        self.assertGreaterEqual(jittered_backoff, 0.0)
        self.assertLessEqual(jittered_backoff, initial_delay * jitter_factor)

    def test_unknown_jitter_type(self):
        """Test that unknown jitter type defaults to full jitter."""
        # Use fixed parameters for testing
        initial_delay = 10.0
        
        # Calculate with unknown jitter type
        with patch('logging.Logger.warning') as mock_warning:
            jittered_backoff = calculate_backoff_with_jitter(
                0, initial_delay, DEFAULT_BACKOFF_FACTOR, DEFAULT_MAX_DELAY, 'unknown')
        
        # Should log a warning
        mock_warning.assert_called_once()
        
        # Should use full jitter (between 0 and base_backoff)
        self.assertGreaterEqual(jittered_backoff, 0.0)
        self.assertLessEqual(jittered_backoff, initial_delay)


class TestRetryWithBackoff(unittest.TestCase):
    """Tests for the retry_with_backoff decorator."""

    def test_successful_execution_no_retry(self):
        """Test that a successful function execution doesn't trigger retries."""
        # Create a mock function that always succeeds
        mock_func = Mock(return_value="success")
        
        # Apply the decorator
        decorated_func = retry_with_backoff()(mock_func)
        
        # Call the decorated function
        result = decorated_func()
        
        # Function should be called exactly once
        mock_func.assert_called_once()
        
        # Result should be the return value of the function
        self.assertEqual(result, "success")

    def test_retry_until_success(self):
        """Test that the function is retried until it succeeds."""
        # Create a mock function that fails twice then succeeds
        mock_func = Mock(side_effect=[ConnectionError("First failure"), 
                                     ConnectionError("Second failure"), 
                                     "success"])
        
        # Mock sleep to avoid waiting during tests
        with patch('time.sleep') as mock_sleep:
            # Apply the decorator with minimal delays
            decorated_func = retry_with_backoff(initial_delay=0.1)(mock_func)
            
            # Call the decorated function
            result = decorated_func()
        
        # Function should be called 3 times (2 failures + 1 success)
        self.assertEqual(mock_func.call_count, 3)
        
        # Sleep should be called twice (after first and second failures)
        self.assertEqual(mock_sleep.call_count, 2)
        
        # Result should be the successful return value
        self.assertEqual(result, "success")

    def test_max_retries_exceeded(self):
        """Test that the function raises an exception after max_retries is exceeded."""
        # Create a mock function that always fails with ConnectionError
        mock_func = Mock(side_effect=ConnectionError("Retryable error"))
        
        # Mock sleep to avoid waiting during tests
        with patch('time.sleep'):
            # Apply the decorator with 2 max retries
            decorated_func = retry_with_backoff(max_retries=2)(mock_func)
            
            # Call the decorated function - should raise the last exception
            with self.assertRaises(ConnectionError):
                decorated_func()
        
        # Function should be called 3 times (initial + 2 retries)
        self.assertEqual(mock_func.call_count, 3)

    def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are raised immediately."""
        # Create a mock function that fails with a non-retryable exception
        mock_func = Mock(side_effect=ValueError("Non-retryable error"))
        
        # Mock sleep to avoid waiting during tests
        with patch('time.sleep') as mock_sleep:
            # Apply the decorator
            decorated_func = retry_with_backoff()(mock_func)
            
            # Call the decorated function - should raise immediately
            with self.assertRaises(ValueError):
                decorated_func()
        
        # Function should be called only once
        mock_func.assert_called_once()
        
        # Sleep should not be called
        mock_sleep.assert_not_called()

    def test_custom_retryable_exceptions(self):
        """Test that custom retryable exceptions are handled correctly."""
        # Create a mock function that fails with ValueError
        mock_func = Mock(side_effect=[ValueError("Custom retryable error"), "success"])
        
        # Mock sleep to avoid waiting during tests
        with patch('time.sleep'):
            # Apply the decorator with custom retryable exceptions
            decorated_func = retry_with_backoff(retryable_exceptions=[ValueError])(mock_func)
            
            # Call the decorated function
            result = decorated_func()
        
        # Function should be called twice (1 failure + 1 success)
        self.assertEqual(mock_func.call_count, 2)
        
        # Result should be the successful return value
        self.assertEqual(result, "success")

    def test_on_retry_callback(self):
        """Test that the on_retry callback is called correctly."""
        # Create a mock function that fails once then succeeds
        mock_func = Mock(side_effect=[ConnectionError("Retryable error"), "success"])
        
        # Create a mock callback
        mock_callback = Mock()
        
        # Mock sleep to avoid waiting during tests
        with patch('time.sleep'):
            # Apply the decorator with the callback
            decorated_func = retry_with_backoff(on_retry=mock_callback)(mock_func)
            
            # Call the decorated function
            result = decorated_func()
        
        # Callback should be called once (before the retry)
        mock_callback.assert_called_once()
        
        # Callback should receive the exception, retry count, and backoff time
        args, _ = mock_callback.call_args
        self.assertIsInstance(args[0], ConnectionError)  # Exception
        self.assertEqual(args[1], 1)  # Retry count
        self.assertIsInstance(args[2], float)  # Backoff time
        
        # Result should be the successful return value
        self.assertEqual(result, "success")


class TestAsyncRetryWithBackoff(unittest.TestCase):
    """Tests for the async_retry_with_backoff decorator."""

    async def async_test_wrapper(self, coro):
        """Helper to run async tests."""
        return await coro

    def test_successful_execution_no_retry(self):
        """Test that a successful async function execution doesn't trigger retries."""
        # Create a mock async function that always succeeds
        mock_func = AsyncMock(return_value="success")
        
        # Apply the decorator
        decorated_func = async_retry_with_backoff()(mock_func)
        
        # Call the decorated function
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(decorated_func())
        
        # Function should be called exactly once
        mock_func.assert_called_once()
        
        # Result should be the return value of the function
        self.assertEqual(result, "success")

    def test_retry_until_success(self):
        """Test that the async function is retried until it succeeds."""
        # Create a mock async function that fails twice then succeeds
        mock_func = AsyncMock(side_effect=[ConnectionError("First failure"), 
                                          ConnectionError("Second failure"), 
                                          "success"])
        
        # Mock asyncio.sleep to avoid waiting during tests
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Apply the decorator with minimal delays
            decorated_func = async_retry_with_backoff(initial_delay=0.1)(mock_func)
            
            # Call the decorated function
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(decorated_func())
        
        # Function should be called 3 times (2 failures + 1 success)
        self.assertEqual(mock_func.call_count, 3)
        
        # Sleep should be called twice (after first and second failures)
        self.assertEqual(mock_sleep.call_count, 2)
        
        # Result should be the successful return value
        self.assertEqual(result, "success")

    def test_max_retries_exceeded(self):
        """Test that the async function raises an exception after max_retries is exceeded."""
        # Create a mock async function that always fails with ConnectionError
        mock_func = AsyncMock(side_effect=ConnectionError("Retryable error"))
        
        # Mock asyncio.sleep to avoid waiting during tests
        with patch('asyncio.sleep', new_callable=AsyncMock):
            # Apply the decorator with 2 max retries
            decorated_func = async_retry_with_backoff(max_retries=2)(mock_func)
            
            # Call the decorated function - should raise the last exception
            loop = asyncio.get_event_loop()
            with self.assertRaises(ConnectionError):
                loop.run_until_complete(decorated_func())
        
        # Function should be called 3 times (initial + 2 retries)
        self.assertEqual(mock_func.call_count, 3)

    def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are raised immediately."""
        # Create a mock async function that fails with a non-retryable exception
        mock_func = AsyncMock(side_effect=ValueError("Non-retryable error"))
        
        # Mock asyncio.sleep to avoid waiting during tests
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Apply the decorator
            decorated_func = async_retry_with_backoff()(mock_func)
            
            # Call the decorated function - should raise immediately
            loop = asyncio.get_event_loop()
            with self.assertRaises(ValueError):
                loop.run_until_complete(decorated_func())
        
        # Function should be called only once
        mock_func.assert_called_once()
        
        # Sleep should not be called
        mock_sleep.assert_not_called()

    def test_on_retry_callback(self):
        """Test that the on_retry callback is called correctly for async functions."""
        # Create a mock async function that fails once then succeeds
        mock_func = AsyncMock(side_effect=[ConnectionError("Retryable error"), "success"])
        
        # Create a mock callback
        mock_callback = Mock()
        
        # Mock asyncio.sleep to avoid waiting during tests
        with patch('asyncio.sleep', new_callable=AsyncMock):
            # Apply the decorator with the callback
            decorated_func = async_retry_with_backoff(on_retry=mock_callback)(mock_func)
            
            # Call the decorated function
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(decorated_func())
        
        # Callback should be called once (before the retry)
        mock_callback.assert_called_once()
        
        # Callback should receive the exception, retry count, and backoff time
        args, _ = mock_callback.call_args
        self.assertIsInstance(args[0], ConnectionError)  # Exception
        self.assertEqual(args[1], 1)  # Retry count
        self.assertIsInstance(args[2], float)  # Backoff time
        
        # Result should be the successful return value
        self.assertEqual(result, "success")


class TestRabbitMQRetry(unittest.TestCase):
    """Tests for the RabbitMQ-specific retry decorators."""

    def test_retry_rabbitmq_publish(self):
        """Test that retry_rabbitmq_publish applies correct parameters."""
        # Mock the retry_with_backoff function
        with patch('src.utils.retry_utils.retry_with_backoff') as mock_retry:
            # Configure mock to return a simple decorator
            mock_retry.return_value = lambda f: f
            
            # Call retry_rabbitmq_publish
            retry_rabbitmq_publish()(lambda: None)
            
            # Verify retry_with_backoff was called with correct parameters
            mock_retry.assert_called_once()
            args, kwargs = mock_retry.call_args
            
            # Check default parameters
            self.assertEqual(kwargs['max_retries'], 5)
            self.assertEqual(kwargs['initial_delay'], 0.5)
            self.assertEqual(kwargs['backoff_factor'], 2.0)
            self.assertEqual(kwargs['max_delay'], 30.0)
            self.assertEqual(kwargs['jitter_type'], 'full')
            
            # Check that retryable_exceptions includes ConnectionError and TimeoutError
            self.assertTrue(ConnectionError in kwargs['retryable_exceptions'])
            self.assertTrue(TimeoutError in kwargs['retryable_exceptions'])

    def test_async_retry_rabbitmq_publish(self):
        """Test that async_retry_rabbitmq_publish applies correct parameters."""
        # Mock the async_retry_with_backoff function
        with patch('src.utils.retry_utils.async_retry_with_backoff') as mock_retry:
            # Configure mock to return a simple decorator
            mock_retry.return_value = lambda f: f
            
            # Call async_retry_rabbitmq_publish
            async_retry_rabbitmq_publish()(lambda: None)
            
            # Verify async_retry_with_backoff was called with correct parameters
            mock_retry.assert_called_once()
            args, kwargs = mock_retry.call_args
            
            # Check default parameters
            self.assertEqual(kwargs['max_retries'], 5)
            self.assertEqual(kwargs['initial_delay'], 0.5)
            self.assertEqual(kwargs['backoff_factor'], 2.0)
            self.assertEqual(kwargs['max_delay'], 30.0)
            self.assertEqual(kwargs['jitter_type'], 'full')
            
            # Check that retryable_exceptions includes ConnectionError and TimeoutError
            self.assertTrue(ConnectionError in kwargs['retryable_exceptions'])
            self.assertTrue(TimeoutError in kwargs['retryable_exceptions'])


class TestIntegration(unittest.TestCase):
    """Integration tests for retry utilities."""

    def test_retry_with_real_time_delays(self):
        """Test retry with actual time delays (minimal for testing)."""
        start_time = time.time()
        
        # Function that fails once then succeeds
        call_count = 0
        
        @retry_with_backoff(max_retries=1, initial_delay=0.01, backoff_factor=1)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Simulated error")
            return "success"
        
        # Call the function
        result = test_function()
        
        # Verify it was called twice
        self.assertEqual(call_count, 2)
        
        # Verify result
        self.assertEqual(result, "success")
        
        # Verify some delay occurred (at least 5ms)
        self.assertGreater(time.time() - start_time, 0.005)

    def test_nested_retries(self):
        """Test that nested retry decorators work correctly."""
        outer_calls = 0
        inner_calls = 0
        
        @retry_with_backoff(max_retries=1, initial_delay=0.01)
        def outer_function():
            nonlocal outer_calls
            outer_calls += 1
            
            if outer_calls == 1:
                raise ConnectionError("Outer error")
            
            return inner_function()
        
        @retry_with_backoff(max_retries=1, initial_delay=0.01)
        def inner_function():
            nonlocal inner_calls
            inner_calls += 1
            
            if inner_calls == 1:
                raise TimeoutError("Inner error")
            
            return "nested success"
        
        # Call the outer function
        result = outer_function()
        
        # Verify call counts
        self.assertEqual(outer_calls, 2)  # Failed once, then succeeded
        self.assertEqual(inner_calls, 2)  # Failed once, then succeeded
        
        # Verify result
        self.assertEqual(result, "nested success")


if __name__ == '__main__':
    unittest.main()