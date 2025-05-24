"""
Unit tests for the retry_utils module.

This module contains tests for retry mechanisms with exponential backoff, jitter,
configurable limits, retry eligibility determination, and decorator-based retry
wrappers to ensure reliable operation during temporary failures.
"""

import asyncio
import time
from unittest import mock
import pytest

from botocore.exceptions import ClientError
from src.utils.retry_utils import (
    calculate_backoff,
    is_retryable_exception,
    is_s3_not_found_error,
    retry,
    async_retry,
    retry_s3_operation,
    async_retry_s3_operation,
    retry_rabbitmq_operation,
    async_retry_rabbitmq_operation,
    DEFAULT_MAX_RETRIES,
    DEFAULT_INITIAL_BACKOFF,
    DEFAULT_MAX_BACKOFF,
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_JITTER_FACTOR,
    RETRYABLE_S3_ERROR_CODES,
    NON_RETRYABLE_S3_ERROR_CODES
)


class TestCalculateBackoff:
    """Tests for the calculate_backoff function."""
    
    def test_initial_backoff(self):
        """Test that the first backoff is close to the initial backoff value."""
        # Disable jitter for deterministic testing
        backoff = calculate_backoff(0, initial_backoff=1.0, jitter_factor=0.0)
        assert backoff == 1.0
    
    def test_exponential_growth(self):
        """Test that backoff grows exponentially with attempt number."""
        # Disable jitter for deterministic testing
        backoff_1 = calculate_backoff(1, initial_backoff=1.0, backoff_factor=2.0, jitter_factor=0.0)
        backoff_2 = calculate_backoff(2, initial_backoff=1.0, backoff_factor=2.0, jitter_factor=0.0)
        backoff_3 = calculate_backoff(3, initial_backoff=1.0, backoff_factor=2.0, jitter_factor=0.0)
        
        assert backoff_1 == 2.0  # 1.0 * (2.0 ^ 1)
        assert backoff_2 == 4.0  # 1.0 * (2.0 ^ 2)
        assert backoff_3 == 8.0  # 1.0 * (2.0 ^ 3)
    
    def test_max_backoff_limit(self):
        """Test that backoff is capped at max_backoff."""
        # Disable jitter for deterministic testing
        backoff = calculate_backoff(
            10,  # Large attempt number
            initial_backoff=1.0,
            max_backoff=30.0,
            backoff_factor=2.0,
            jitter_factor=0.0
        )
        assert backoff == 30.0  # Should be capped at max_backoff
    
    def test_jitter_range(self):
        """Test that jitter is applied within the expected range."""
        # Mock random.uniform to return a fixed value for testing
        with mock.patch('random.uniform', return_value=0.05):
            # With jitter of 0.1 (10% of 1.0)
            backoff = calculate_backoff(0, initial_backoff=1.0, jitter_factor=0.1)
            assert backoff == 1.05  # 1.0 + 0.05
        
        with mock.patch('random.uniform', return_value=-0.05):
            # With jitter of 0.1 (10% of 1.0)
            backoff = calculate_backoff(0, initial_backoff=1.0, jitter_factor=0.1)
            assert backoff == 0.95  # 1.0 - 0.05
    
    def test_never_negative_backoff(self):
        """Test that backoff is never negative, even with large negative jitter."""
        # Force a large negative jitter that would make backoff negative
        with mock.patch('random.uniform', return_value=-2.0):
            backoff = calculate_backoff(0, initial_backoff=1.0, jitter_factor=1.0)
            assert backoff == 0.001  # Minimum value


class TestRetryEligibility:
    """Tests for retry eligibility determination functions."""
    
    def test_retryable_standard_exceptions(self):
        """Test that standard retryable exceptions are correctly identified."""
        assert is_retryable_exception(ConnectionError())
        assert is_retryable_exception(TimeoutError())
    
    def test_non_retryable_standard_exceptions(self):
        """Test that standard non-retryable exceptions are correctly identified."""
        assert not is_retryable_exception(ValueError())
        assert not is_retryable_exception(KeyError())
        assert not is_retryable_exception(TypeError())
    
    @pytest.mark.parametrize("error_code", list(RETRYABLE_S3_ERROR_CODES)[:3])  # Test first 3 codes
    def test_retryable_s3_error_codes(self, error_code):
        """Test that S3 errors with retryable codes are correctly identified."""
        # Create a mock ClientError with the specified error code
        client_error = ClientError(
            {
                'Error': {'Code': error_code},
                'ResponseMetadata': {'HTTPStatusCode': 500}
            },
            'GetObject'
        )
        assert is_retryable_exception(client_error)
    
    @pytest.mark.parametrize("error_code", list(NON_RETRYABLE_S3_ERROR_CODES)[:3])  # Test first 3 codes
    def test_non_retryable_s3_error_codes(self, error_code):
        """Test that S3 errors with non-retryable codes are correctly identified."""
        # Create a mock ClientError with the specified error code
        client_error = ClientError(
            {
                'Error': {'Code': error_code},
                'ResponseMetadata': {'HTTPStatusCode': 400}
            },
            'GetObject'
        )
        assert not is_retryable_exception(client_error)
    
    def test_retryable_http_status_codes(self):
        """Test that errors with retryable HTTP status codes are correctly identified."""
        # Create a mock exception with a status_code attribute
        class MockHTTPError(Exception):
            def __init__(self, status_code):
                self.status_code = status_code
        
        assert is_retryable_exception(MockHTTPError(500))
        assert is_retryable_exception(MockHTTPError(502))
        assert is_retryable_exception(MockHTTPError(503))
        assert is_retryable_exception(MockHTTPError(504))
    
    def test_non_retryable_http_status_codes(self):
        """Test that errors with non-retryable HTTP status codes are correctly identified."""
        # Create a mock exception with a status_code attribute
        class MockHTTPError(Exception):
            def __init__(self, status_code):
                self.status_code = status_code
        
        assert not is_retryable_exception(MockHTTPError(400))
        assert not is_retryable_exception(MockHTTPError(401))
        assert not is_retryable_exception(MockHTTPError(403))
        assert not is_retryable_exception(MockHTTPError(404))
    
    def test_s3_not_found_error_detection(self):
        """Test that S3 not found errors are correctly identified."""
        # Test with NoSuchKey error code
        client_error = ClientError(
            {
                'Error': {'Code': 'NoSuchKey'},
                'ResponseMetadata': {'HTTPStatusCode': 404}
            },
            'GetObject'
        )
        assert is_s3_not_found_error(client_error)
        
        # Test with NoSuchBucket error code
        client_error = ClientError(
            {
                'Error': {'Code': 'NoSuchBucket'},
                'ResponseMetadata': {'HTTPStatusCode': 404}
            },
            'GetObject'
        )
        assert is_s3_not_found_error(client_error)
        
        # Test with 404 status code
        class MockHTTPError(Exception):
            def __init__(self, status_code):
                self.status_code = status_code
        
        assert is_s3_not_found_error(MockHTTPError(404))


class TestRetryDecorator:
    """Tests for the retry decorator."""
    
    def test_successful_execution_no_retry(self):
        """Test that a successful function execution doesn't trigger retries."""
        mock_func = mock.Mock(return_value="success")
        decorated_func = retry()(mock_func)
        
        result = decorated_func("arg1", kwarg1="value1")
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
    
    def test_retry_on_retryable_exception(self):
        """Test that retryable exceptions trigger retries."""
        # Mock function that raises ConnectionError twice, then succeeds
        mock_func = mock.Mock(side_effect=[ConnectionError(), ConnectionError(), "success"])
        decorated_func = retry(max_retries=3)(mock_func)
        
        # Mock sleep to avoid actual delays in tests
        with mock.patch('time.sleep') as mock_sleep:
            result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep called for each retry
    
    def test_retry_exhaustion(self):
        """Test that retry exhaustion raises the last exception."""
        # Mock function that always raises ConnectionError
        mock_func = mock.Mock(side_effect=ConnectionError("persistent error"))
        decorated_func = retry(max_retries=2)(mock_func)
        
        # Mock sleep to avoid actual delays in tests
        with mock.patch('time.sleep'):
            with pytest.raises(ConnectionError, match="persistent error"):
                decorated_func()
        
        assert mock_func.call_count == 3  # Initial attempt + 2 retries
    
    def test_no_retry_on_non_retryable_exception(self):
        """Test that non-retryable exceptions don't trigger retries."""
        # Mock function that raises ValueError
        mock_func = mock.Mock(side_effect=ValueError("invalid value"))
        decorated_func = retry(max_retries=3)(mock_func)
        
        # Mock sleep to avoid actual delays in tests
        with mock.patch('time.sleep') as mock_sleep:
            with pytest.raises(ValueError, match="invalid value"):
                decorated_func()
        
        assert mock_func.call_count == 1  # Only the initial attempt
        assert mock_sleep.call_count == 0  # No retries, no sleep
    
    def test_retry_with_custom_exceptions(self):
        """Test retry with custom retryable exceptions."""
        # Define a custom exception
        class CustomError(Exception):
            pass
        
        # Mock function that raises CustomError twice, then succeeds
        mock_func = mock.Mock(side_effect=[CustomError(), CustomError(), "success"])
        decorated_func = retry(max_retries=3, retryable_exceptions=(CustomError,))(mock_func)
        
        # Mock sleep to avoid actual delays in tests
        with mock.patch('time.sleep'):
            result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_retry_on_result_condition(self):
        """Test retry based on result condition."""
        # Define a result condition that retries on None
        def retry_on_none(result):
            return result is None
        
        # Mock function that returns None twice, then a value
        mock_func = mock.Mock(side_effect=[None, None, "success"])
        decorated_func = retry(max_retries=3, retry_on_result=retry_on_none)(mock_func)
        
        # Mock sleep to avoid actual delays in tests
        with mock.patch('time.sleep'):
            result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_backoff_timing(self):
        """Test that backoff timing follows the expected pattern."""
        # Mock function that raises ConnectionError until retries are exhausted
        mock_func = mock.Mock(side_effect=ConnectionError("persistent error"))
        decorated_func = retry(
            max_retries=3,
            initial_backoff=1.0,
            backoff_factor=2.0,
            jitter_factor=0.0  # Disable jitter for deterministic testing
        )(mock_func)
        
        # Mock sleep to capture sleep durations
        sleep_times = []
        
        def mock_sleep_func(seconds):
            sleep_times.append(seconds)
        
        with mock.patch('time.sleep', side_effect=mock_sleep_func):
            with pytest.raises(ConnectionError):
                decorated_func()
        
        # Check backoff timing: 1.0, 2.0, 4.0
        assert len(sleep_times) == 3
        assert sleep_times[0] == 1.0
        assert sleep_times[1] == 2.0
        assert sleep_times[2] == 4.0


class TestAsyncRetryDecorator:
    """Tests for the async_retry decorator."""
    
    @pytest.mark.asyncio
    async def test_async_successful_execution_no_retry(self):
        """Test that a successful async function execution doesn't trigger retries."""
        mock_func = mock.AsyncMock(return_value="success")
        decorated_func = async_retry()(mock_func)
        
        result = await decorated_func("arg1", kwarg1="value1")
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
    
    @pytest.mark.asyncio
    async def test_async_retry_on_retryable_exception(self):
        """Test that retryable exceptions trigger retries in async functions."""
        # Mock async function that raises ConnectionError twice, then succeeds
        mock_func = mock.AsyncMock(side_effect=[ConnectionError(), ConnectionError(), "success"])
        decorated_func = async_retry(max_retries=3)(mock_func)
        
        # Mock asyncio.sleep to avoid actual delays in tests
        with mock.patch('asyncio.sleep', new_callable=mock.AsyncMock) as mock_sleep:
            result = await decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep called for each retry
    
    @pytest.mark.asyncio
    async def test_async_retry_exhaustion(self):
        """Test that retry exhaustion raises the last exception in async functions."""
        # Mock async function that always raises ConnectionError
        mock_func = mock.AsyncMock(side_effect=ConnectionError("persistent error"))
        decorated_func = async_retry(max_retries=2)(mock_func)
        
        # Mock asyncio.sleep to avoid actual delays in tests
        with mock.patch('asyncio.sleep', new_callable=mock.AsyncMock):
            with pytest.raises(ConnectionError, match="persistent error"):
                await decorated_func()
        
        assert mock_func.call_count == 3  # Initial attempt + 2 retries
    
    @pytest.mark.asyncio
    async def test_async_no_retry_on_non_retryable_exception(self):
        """Test that non-retryable exceptions don't trigger retries in async functions."""
        # Mock async function that raises ValueError
        mock_func = mock.AsyncMock(side_effect=ValueError("invalid value"))
        decorated_func = async_retry(max_retries=3)(mock_func)
        
        # Mock asyncio.sleep to avoid actual delays in tests
        with mock.patch('asyncio.sleep', new_callable=mock.AsyncMock) as mock_sleep:
            with pytest.raises(ValueError, match="invalid value"):
                await decorated_func()
        
        assert mock_func.call_count == 1  # Only the initial attempt
        assert mock_sleep.call_count == 0  # No retries, no sleep
    
    @pytest.mark.asyncio
    async def test_async_retry_on_result_condition(self):
        """Test retry based on result condition in async functions."""
        # Define a result condition that retries on None
        def retry_on_none(result):
            return result is None
        
        # Mock async function that returns None twice, then a value
        mock_func = mock.AsyncMock(side_effect=[None, None, "success"])
        decorated_func = async_retry(max_retries=3, retry_on_result=retry_on_none)(mock_func)
        
        # Mock asyncio.sleep to avoid actual delays in tests
        with mock.patch('asyncio.sleep', new_callable=mock.AsyncMock):
            result = await decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_async_backoff_timing(self):
        """Test that backoff timing follows the expected pattern in async functions."""
        # Mock async function that raises ConnectionError until retries are exhausted
        mock_func = mock.AsyncMock(side_effect=ConnectionError("persistent error"))
        decorated_func = async_retry(
            max_retries=3,
            initial_backoff=1.0,
            backoff_factor=2.0,
            jitter_factor=0.0  # Disable jitter for deterministic testing
        )(mock_func)
        
        # Mock asyncio.sleep to capture sleep durations
        sleep_times = []
        
        async def mock_sleep_func(seconds):
            sleep_times.append(seconds)
        
        with mock.patch('asyncio.sleep', side_effect=mock_sleep_func):
            with pytest.raises(ConnectionError):
                await decorated_func()
        
        # Check backoff timing: 1.0, 2.0, 4.0
        assert len(sleep_times) == 3
        assert sleep_times[0] == 1.0
        assert sleep_times[1] == 2.0
        assert sleep_times[2] == 4.0


class TestSpecializedRetryDecorators:
    """Tests for specialized retry decorators for S3 and RabbitMQ operations."""
    
    def test_retry_s3_operation(self):
        """Test the retry_s3_operation decorator with S3-specific settings."""
        # Mock function that raises S3 error, then succeeds
        mock_func = mock.Mock(side_effect=[
            ClientError(
                {
                    'Error': {'Code': 'InternalError'},
                    'ResponseMetadata': {'HTTPStatusCode': 500}
                },
                'GetObject'
            ),
            "success"
        ])
        
        decorated_func = retry_s3_operation(mock_func)
        
        # Mock sleep to avoid actual delays in tests
        with mock.patch('time.sleep'):
            result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_retry_s3_operation_custom_retries(self):
        """Test the retry_s3_operation decorator with custom max_retries."""
        # Mock function that raises S3 error multiple times
        mock_func = mock.Mock(side_effect=[
            ClientError(
                {
                    'Error': {'Code': 'ServiceUnavailable'},
                    'ResponseMetadata': {'HTTPStatusCode': 503}
                },
                'GetObject'
            )
        ] * 10)  # Always fails
        
        # Set custom max_retries=2
        decorated_func = retry_s3_operation(mock_func, max_retries=2)
        
        # Mock sleep to avoid actual delays in tests
        with mock.patch('time.sleep'):
            with pytest.raises(ClientError):
                decorated_func()
        
        assert mock_func.call_count == 3  # Initial + 2 retries
    
    @pytest.mark.asyncio
    async def test_async_retry_s3_operation(self):
        """Test the async_retry_s3_operation decorator."""
        # Mock async function that raises S3 error, then succeeds
        mock_func = mock.AsyncMock(side_effect=[
            ClientError(
                {
                    'Error': {'Code': 'RequestTimeout'},
                    'ResponseMetadata': {'HTTPStatusCode': 408}
                },
                'GetObject'
            ),
            "success"
        ])
        
        decorated_func = async_retry_s3_operation(mock_func)
        
        # Mock asyncio.sleep to avoid actual delays in tests
        with mock.patch('asyncio.sleep', new_callable=mock.AsyncMock):
            result = await decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_retry_rabbitmq_operation(self):
        """Test the retry_rabbitmq_operation decorator with RabbitMQ-specific settings."""
        # Define a RabbitMQ-like exception
        class RabbitMQConnectionError(ConnectionError):
            pass
        
        # Mock function that raises RabbitMQ error, then succeeds
        mock_func = mock.Mock(side_effect=[RabbitMQConnectionError(), "success"])
        decorated_func = retry_rabbitmq_operation(mock_func)
        
        # Mock sleep to avoid actual delays in tests
        with mock.patch('time.sleep'):
            result = decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_async_retry_rabbitmq_operation(self):
        """Test the async_retry_rabbitmq_operation decorator."""
        # Define a RabbitMQ-like exception
        class RabbitMQConnectionError(ConnectionError):
            pass
        
        # Mock async function that raises RabbitMQ error, then succeeds
        mock_func = mock.AsyncMock(side_effect=[RabbitMQConnectionError(), "success"])
        decorated_func = async_retry_rabbitmq_operation(mock_func)
        
        # Mock asyncio.sleep to avoid actual delays in tests
        with mock.patch('asyncio.sleep', new_callable=mock.AsyncMock):
            result = await decorated_func()
        
        assert result == "success"
        assert mock_func.call_count == 2


class TestIntegrationScenarios:
    """Integration tests for retry utilities in realistic scenarios."""
    
    def test_s3_document_download_retry(self):
        """Test retry logic for S3 document download with temporary failures."""
        # Mock S3 client with get_object method that fails temporarily
        mock_s3_client = mock.Mock()
        mock_s3_client.get_object.side_effect = [
            ClientError(
                {
                    'Error': {'Code': 'SlowDown'},
                    'ResponseMetadata': {'HTTPStatusCode': 503}
                },
                'GetObject'
            ),
            # Second attempt succeeds
            {
                'Body': mock.Mock(read=mock.Mock(return_value=b'document content')),
                'ContentLength': 15,
                'ContentType': 'application/pdf'
            }
        ]
        
        # Function to download document from S3
        @retry_s3_operation
        def download_document(bucket, key):
            response = mock_s3_client.get_object(Bucket=bucket, Key=key)
            return response['Body'].read()
        
        # Mock sleep to avoid actual delays in tests
        with mock.patch('time.sleep'):
            content = download_document('mca-documents', 'application123.pdf')
        
        assert content == b'document content'
        assert mock_s3_client.get_object.call_count == 2
        mock_s3_client.get_object.assert_called_with(Bucket='mca-documents', Key='application123.pdf')
    
    @pytest.mark.asyncio
    async def test_async_rabbitmq_publish_retry(self):
        """Test async retry logic for RabbitMQ message publishing with temporary failures."""
        # Mock RabbitMQ channel with publish method that fails temporarily
        mock_channel = mock.AsyncMock()
        mock_channel.basic_publish.side_effect = [
            ConnectionError("Connection reset by peer"),
            # Second attempt succeeds
            None
        ]
        
        # Function to publish message to RabbitMQ
        @async_retry_rabbitmq_operation
        async def publish_message(exchange, routing_key, body):
            await mock_channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=body
            )
            return True
        
        # Mock asyncio.sleep to avoid actual delays in tests
        with mock.patch('asyncio.sleep', new_callable=mock.AsyncMock):
            result = await publish_message('mca.documents', 'document.new', '{"id": "doc123"}')
        
        assert result is True
        assert mock_channel.basic_publish.call_count == 2
        mock_channel.basic_publish.assert_called_with(
            exchange='mca.documents',
            routing_key='document.new',
            body='{"id": "doc123"}'
        )
    
    def test_retry_with_dynamic_eligibility_check(self):
        """Test retry with dynamic eligibility check based on exception attributes."""
        # Create a custom exception with status_code attribute
        class APIError(Exception):
            def __init__(self, status_code, message):
                self.status_code = status_code
                self.message = message
                super().__init__(f"{status_code}: {message}")
        
        # Function that determines if an APIError is retryable based on status code
        def is_api_error_retryable(exception):
            if isinstance(exception, APIError):
                # Only retry on 5xx errors, not 4xx
                return 500 <= exception.status_code < 600
            return False
        
        # Mock function that raises different API errors
        mock_func = mock.Mock(side_effect=[
            APIError(503, "Service Unavailable"),  # Retryable
            APIError(404, "Not Found"),  # Not retryable
            "success"
        ])
        
        # Custom retry decorator that uses our eligibility check
        def custom_retry(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                for attempt in range(3):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt < 2 and is_api_error_retryable(e):
                            # Would sleep here in real code
                            continue
                        raise
            return wrapper
        
        decorated_func = custom_retry(mock_func)
        
        # First call should retry on 503 and then fail on 404
        with pytest.raises(APIError) as excinfo:
            decorated_func()
        
        assert "404: Not Found" in str(excinfo.value)
        assert mock_func.call_count == 2  # Called twice (503, then 404)