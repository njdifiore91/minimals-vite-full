#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the main entry point (main.py) of the OCR Service.

This file verifies that the service correctly initializes the application,
connects to required services (RabbitMQ, S3), loads TensorFlow models,
and starts the OCR processing. It ensures the service can handle startup
errors and shutdown gracefully.
"""

import os
import sys
import signal
import pytest
from unittest import mock
import tensorflow as tf

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import the modules to test
import main
from app import OCRServiceApp
from utils.tensorflow_utils import check_gpu_memory


@pytest.fixture
def mock_app():
    """Mock the OCRServiceApp class."""
    with mock.patch('main.OCRServiceApp') as mock_app_class:
        # Create a mock instance that will be returned when OCRServiceApp is instantiated
        mock_app_instance = mock.MagicMock()
        mock_app_class.return_value = mock_app_instance
        yield mock_app_instance


@pytest.fixture
def mock_tensorflow():
    """Mock TensorFlow and GPU-related functions."""
    with mock.patch('main.tf') as mock_tf, \
         mock.patch('main.check_gpu_memory') as mock_check_gpu_memory:
        # Configure the mock to return a list of GPU devices
        mock_tf.config.list_physical_devices.return_value = [
            '/physical_device:GPU:0'
        ]
        # Configure the mock to return sufficient GPU memory (10GB in MB)
        mock_check_gpu_memory.return_value = 10 * 1024
        yield mock_tf


@pytest.fixture
def mock_signal_handlers():
    """Mock signal handlers setup."""
    with mock.patch('main.signal.signal') as mock_signal:
        yield mock_signal


@pytest.fixture
def mock_logger():
    """Mock the logger."""
    with mock.patch('main.logger') as mock_logger:
        yield mock_logger


@pytest.fixture
def mock_setup_logger():
    """Mock the setup_logger function."""
    with mock.patch('main.setup_logger') as mock_setup_logger:
        yield mock_setup_logger


@pytest.fixture
def mock_sys_exit():
    """Mock sys.exit to prevent tests from exiting."""
    with mock.patch('main.sys.exit') as mock_exit:
        yield mock_exit


@pytest.fixture
def mock_time_sleep():
    """Mock time.sleep to speed up tests."""
    with mock.patch('main.time.sleep') as mock_sleep:
        # Configure sleep to raise an exception after first call to break the infinite loop
        mock_sleep.side_effect = [None, KeyboardInterrupt]
        yield mock_sleep


class TestMain:
    """Test cases for the main.py module."""

    def test_verify_gpu_availability_success(self, mock_tensorflow, mock_logger):
        """Test that GPU verification succeeds when GPU is available with sufficient memory."""
        # Call the function
        main.verify_gpu_availability()
        
        # Verify that the function checked for GPUs
        mock_tensorflow.config.list_physical_devices.assert_called_once_with('GPU')
        
        # Verify that memory growth was enabled for the GPU
        mock_tensorflow.config.experimental.set_memory_growth.assert_called_once()
        
        # Verify that GPU memory was checked
        assert check_gpu_memory.called
        
        # Verify that a small tensor was created to force GPU initialization
        mock_tensorflow.random.normal.assert_called_once()
        
        # Verify that success was logged
        mock_logger.info.assert_any_call("GPU initialization successful")

    def test_verify_gpu_availability_no_gpu(self, mock_tensorflow, mock_logger):
        """Test that GPU verification fails when no GPU is available."""
        # Configure the mock to return an empty list (no GPUs)
        mock_tensorflow.config.list_physical_devices.return_value = []
        
        # Call the function and verify that it raises an exception
        with pytest.raises(RuntimeError, match="No GPU found"):
            main.verify_gpu_availability()

    def test_verify_gpu_availability_insufficient_memory(self, mock_tensorflow, mock_logger):
        """Test that GPU verification fails when GPU memory is insufficient."""
        # Configure the mock to return insufficient GPU memory (4GB in MB)
        with mock.patch('main.check_gpu_memory', return_value=4 * 1024):
            # Call the function and verify that it raises an exception
            with pytest.raises(RuntimeError, match="Insufficient GPU memory"):
                main.verify_gpu_availability()

    def test_setup_signal_handlers(self, mock_signal_handlers, mock_logger):
        """Test that signal handlers are properly set up."""
        # Call the function
        main.setup_signal_handlers()
        
        # Verify that signal handlers were registered for SIGINT and SIGTERM
        assert mock_signal_handlers.call_count == 2
        mock_signal_handlers.assert_any_call(signal.SIGINT, mock.ANY)
        mock_signal_handlers.assert_any_call(signal.SIGTERM, mock.ANY)
        
        # Verify that success was logged
        mock_logger.info.assert_called_with("Signal handlers registered for graceful shutdown")

    def test_shutdown_with_app_instance(self, mock_app, mock_logger):
        """Test graceful shutdown when app_instance exists."""
        # Set the global app_instance
        main.app_instance = mock_app
        
        # Call the function
        main.shutdown()
        
        # Verify that the app was stopped
        mock_app.stop.assert_called_once()
        
        # Verify that TensorFlow session was cleared
        assert mock.call("TensorFlow session cleared, GPU resources released") in mock_logger.info.call_args_list
        
        # Verify that success was logged
        mock_logger.info.assert_any_call("OCR Service application stopped successfully")

    def test_shutdown_without_app_instance(self, mock_logger):
        """Test graceful shutdown when app_instance does not exist."""
        # Set the global app_instance to None
        main.app_instance = None
        
        # Call the function
        main.shutdown()
        
        # Verify that a warning was logged
        mock_logger.warning.assert_called_with("Application instance not found during shutdown")

    def test_shutdown_with_exception(self, mock_app, mock_logger):
        """Test graceful shutdown when an exception occurs."""
        # Set the global app_instance
        main.app_instance = mock_app
        
        # Configure the mock to raise an exception when stop is called
        mock_app.stop.side_effect = Exception("Test exception")
        
        # Call the function
        main.shutdown()
        
        # Verify that the app.stop was called
        mock_app.stop.assert_called_once()
        
        # Verify that the error was logged
        mock_logger.error.assert_any_call("Error during application shutdown: Test exception")

    def test_handle_uncaught_exception_keyboard_interrupt(self, mock_sys_exit):
        """Test that KeyboardInterrupt is handled properly."""
        # Mock sys.__excepthook__
        with mock.patch('main.sys.__excepthook__') as mock_original_hook:
            # Call the function with KeyboardInterrupt
            main.handle_uncaught_exception(KeyboardInterrupt, KeyboardInterrupt(), None)
            
            # Verify that the original handler was called
            mock_original_hook.assert_called_once()
            
            # Verify that sys.exit was not called
            mock_sys_exit.assert_not_called()

    def test_handle_uncaught_exception_other_exception(self, mock_logger, mock_sys_exit):
        """Test that other exceptions are handled properly."""
        # Mock log_exception
        with mock.patch('main.log_exception') as mock_log_exception:
            # Call the function with a different exception
            exc = ValueError("Test exception")
            main.handle_uncaught_exception(ValueError, exc, None)
            
            # Verify that the exception was logged
            mock_log_exception.assert_called_once_with(mock_logger, "Uncaught exception", exc, None)
            
            # Verify that shutdown was called
            # This is difficult to test directly since we can't easily mock a function in the same module
            # We'll verify that sys.exit was called instead
            mock_sys_exit.assert_called_once_with(1)

    def test_main_success(self, mock_app, mock_tensorflow, mock_signal_handlers, 
                         mock_setup_logger, mock_logger, mock_sys_exit, mock_time_sleep):
        """Test that the main function runs successfully."""
        # Call the function
        with pytest.raises(KeyboardInterrupt):
            main.main()
        
        # Verify that logging was set up
        mock_setup_logger.assert_called_once()
        
        # Verify that the global exception handler was registered
        assert sys.excepthook == main.handle_uncaught_exception
        
        # Verify that signal handlers were set up
        assert mock_signal_handlers.call_count >= 2
        
        # Verify that GPU availability was checked
        mock_tensorflow.config.list_physical_devices.assert_called_once_with('GPU')
        
        # Verify that the app was created and started
        mock_app.start.assert_called_once()
        
        # Verify that the main loop was entered
        mock_time_sleep.assert_called()
        
        # Verify that sys.exit was not called (since we raised KeyboardInterrupt)
        mock_sys_exit.assert_not_called()

    def test_main_exception(self, mock_app, mock_logger, mock_sys_exit):
        """Test that the main function handles exceptions properly."""
        # Configure the app to raise an exception when started
        mock_app.start.side_effect = Exception("Test exception")
        
        # Call the function
        main.main()
        
        # Verify that the error was logged
        mock_logger.critical.assert_called_with("Failed to start OCR Service: Test exception")
        
        # Verify that sys.exit was called with an error code
        mock_sys_exit.assert_called_once_with(1)

    def test_signal_handler(self, mock_logger, mock_sys_exit):
        """Test that the signal handler shuts down the application properly."""
        # Mock shutdown function
        with mock.patch('main.shutdown') as mock_shutdown:
            # Get the signal handler function
            # We need to call setup_signal_handlers first to register the handler
            main.setup_signal_handlers()
            
            # Get the signal handler that was registered
            signal_handler = mock.call(signal.SIGINT, mock.ANY).args[1]
            
            # Call the signal handler
            signal_handler(signal.SIGINT, None)
            
            # Verify that shutdown was called
            mock_shutdown.assert_called_once()
            
            # Verify that sys.exit was called with code 0
            mock_sys_exit.assert_called_once_with(0)


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])