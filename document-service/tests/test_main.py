#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the main entry point (main.py) of the Document Service.

This module contains tests that verify the Document Service correctly initializes
the application, connects to required services (RabbitMQ, S3), loads ML models,
and starts the document classification process. It also tests error handling and
graceful shutdown.
"""

import os
import sys
import signal
import asyncio
import logging
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call

# Import the main module
try:
    from src.main import main, run_service, handle_exception
except ImportError:
    # If the module is not available, we'll mock it in the tests
    pass


# ===== Test Application Initialization =====

@pytest.mark.asyncio
async def test_main_initializes_application(mock_application):
    """Test that the main function initializes the application correctly."""
    # Patch the get_app function to return our mock application
    with patch("src.main.get_app", return_value=mock_application):
        # Patch asyncio.sleep to avoid infinite loop
        with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
            # Run the main function
            with pytest.raises(asyncio.CancelledError):
                await main()
            
            # Verify the application was started
            mock_application.start.assert_called_once()
            # Verify signal handlers were set up
            mock_application.setup_signal_handlers.assert_called_once()


@pytest.mark.asyncio
async def test_main_handles_keyboard_interrupt(mock_application):
    """Test that the main function handles keyboard interrupts gracefully."""
    # Patch the get_app function to return our mock application
    with patch("src.main.get_app", return_value=mock_application):
        # Patch asyncio.sleep to raise KeyboardInterrupt
        with patch("asyncio.sleep", side_effect=KeyboardInterrupt()):
            # Run the main function
            await main()
            
            # Verify the application was started and stopped
            mock_application.start.assert_called_once()
            mock_application.stop.assert_called_once()


@pytest.mark.asyncio
async def test_main_handles_general_exceptions(mock_application):
    """Test that the main function handles general exceptions gracefully."""
    # Patch the get_app function to return our mock application
    with patch("src.main.get_app", return_value=mock_application):
        # Make the start method raise an exception
        mock_application.start.side_effect = Exception("Test exception")
        
        # Run the main function
        await main()
        
        # Verify the application was started and stopped
        mock_application.start.assert_called_once()
        mock_application.stop.assert_called_once()


# ===== Test Run Service Function =====

def test_run_service_creates_event_loop():
    """Test that run_service creates an event loop if none exists."""
    # Patch asyncio.get_event_loop to raise RuntimeError
    with patch("asyncio.get_event_loop", side_effect=RuntimeError("No event loop")):
        # Patch asyncio.new_event_loop and set_event_loop
        with patch("asyncio.new_event_loop") as mock_new_loop:
            with patch("asyncio.set_event_loop") as mock_set_loop:
                # Patch the main function to avoid actually running it
                with patch("src.main.main", new_callable=AsyncMock):
                    # Patch logging_config to avoid actual logging configuration
                    with patch("src.config.logging_config.configure_logging"):
                        # Run the service
                        run_service()
                        
                        # Verify a new event loop was created and set
                        mock_new_loop.assert_called_once()
                        mock_set_loop.assert_called_once_with(mock_new_loop.return_value)


def test_run_service_uses_existing_event_loop():
    """Test that run_service uses an existing event loop if one exists."""
    # Patch asyncio.get_event_loop
    with patch("asyncio.get_event_loop") as mock_get_loop:
        # Patch the main function to avoid actually running it
        with patch("src.main.main", new_callable=AsyncMock):
            # Patch logging_config to avoid actual logging configuration
            with patch("src.config.logging_config.configure_logging"):
                # Run the service
                run_service()
                
                # Verify the existing event loop was used
                mock_get_loop.assert_called_once()
                mock_get_loop.return_value.run_until_complete.assert_called_once()


def test_run_service_handles_keyboard_interrupt():
    """Test that run_service handles keyboard interrupts gracefully."""
    # Patch asyncio.get_event_loop
    with patch("asyncio.get_event_loop") as mock_get_loop:
        # Make run_until_complete raise KeyboardInterrupt
        mock_get_loop.return_value.run_until_complete.side_effect = KeyboardInterrupt()
        
        # Patch logging_config to avoid actual logging configuration
        with patch("src.config.logging_config.configure_logging"):
            # Run the service
            run_service()
            
            # Verify the event loop was closed
            mock_get_loop.return_value.close.assert_called_once()


# ===== Test Exception Handling =====

def test_handle_exception_for_keyboard_interrupt():
    """Test that handle_exception doesn't log KeyboardInterrupt as an error."""
    # Patch sys.__excepthook__
    with patch("sys.__excepthook__") as mock_excepthook:
        # Call handle_exception with KeyboardInterrupt
        handle_exception(KeyboardInterrupt, KeyboardInterrupt(), None)
        
        # Verify sys.__excepthook__ was called
        mock_excepthook.assert_called_once_with(KeyboardInterrupt, KeyboardInterrupt(), None)


def test_handle_exception_for_general_exceptions(caplog):
    """Test that handle_exception logs general exceptions as critical errors."""
    # Set up logging to capture log messages
    caplog.set_level(logging.CRITICAL)
    
    # Patch sys.exit to avoid actually exiting
    with patch("sys.exit") as mock_exit:
        # Call handle_exception with a general exception
        exception = Exception("Test exception")
        handle_exception(Exception, exception, None)
        
        # Verify the exception was logged as critical
        assert "Uncaught exception" in caplog.text
        assert "Test exception" in caplog.text
        
        # Verify sys.exit was called with error code 1
        mock_exit.assert_called_once_with(1)


# ===== Test Signal Handling =====

@pytest.mark.asyncio
async def test_signal_handler_setup(mock_application):
    """Test that signal handlers are set up correctly."""
    # Patch the get_app function to return our mock application
    with patch("src.main.get_app", return_value=mock_application):
        # Patch signal.signal
        with patch("signal.signal") as mock_signal:
            # Patch asyncio.sleep to avoid infinite loop
            with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
                # Run the main function
                with pytest.raises(asyncio.CancelledError):
                    await main()
                
                # Verify signal handlers were set up
                mock_application.setup_signal_handlers.assert_called_once()


# ===== Test Application Start/Stop =====

@pytest.mark.asyncio
async def test_application_start_connects_to_rabbitmq(mock_application):
    """Test that the application connects to RabbitMQ when started."""
    # Patch the get_app function to return our mock application
    with patch("src.main.get_app", return_value=mock_application):
        # Patch asyncio.sleep to avoid infinite loop
        with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
            # Run the main function
            with pytest.raises(asyncio.CancelledError):
                await main()
            
            # Verify the application was started
            mock_application.start.assert_called_once()
            
            # Verify RabbitMQ connection was established
            # This assumes the queue_service.connect method is called during application start
            mock_application.queue_service.connect.assert_called_once()


@pytest.mark.asyncio
async def test_application_start_connects_to_s3(mock_application):
    """Test that the application connects to S3 when started."""
    # Patch the get_app function to return our mock application
    with patch("src.main.get_app", return_value=mock_application):
        # Patch asyncio.sleep to avoid infinite loop
        with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
            # Run the main function
            with pytest.raises(asyncio.CancelledError):
                await main()
            
            # Verify the application was started
            mock_application.start.assert_called_once()
            
            # Verify S3 connection was established
            # This assumes the storage_service.connect method is called during application start
            mock_application.storage_service.connect.assert_called_once()


@pytest.mark.asyncio
async def test_application_start_initializes_classification_service(mock_application):
    """Test that the application initializes the classification service when started."""
    # Patch the get_app function to return our mock application
    with patch("src.main.get_app", return_value=mock_application):
        # Patch asyncio.sleep to avoid infinite loop
        with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
            # Run the main function
            with pytest.raises(asyncio.CancelledError):
                await main()
            
            # Verify the application was started
            mock_application.start.assert_called_once()
            
            # Verify classification service was initialized
            # This assumes the classification_service.initialize method is called during application start
            mock_application.classification_service.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_application_stop_cleans_up_resources(mock_application):
    """Test that the application cleans up resources when stopped."""
    # Patch the get_app function to return our mock application
    with patch("src.main.get_app", return_value=mock_application):
        # Patch asyncio.sleep to raise KeyboardInterrupt
        with patch("asyncio.sleep", side_effect=KeyboardInterrupt()):
            # Run the main function
            await main()
            
            # Verify the application was stopped
            mock_application.stop.assert_called_once()
            
            # Verify resources were cleaned up
            # This assumes these methods are called during application stop
            mock_application.queue_service.disconnect.assert_called_once()
            mock_application.storage_service.disconnect.assert_called_once()
            mock_application.classification_service.cleanup.assert_called_once()


# ===== Test Logging Configuration =====

def test_logging_configuration_on_startup():
    """Test that logging is configured on startup."""
    # Patch logging_config.configure_logging
    with patch("src.config.logging_config.configure_logging") as mock_configure_logging:
        # Patch asyncio.get_event_loop
        with patch("asyncio.get_event_loop"):
            # Patch the main function to avoid actually running it
            with patch("src.main.main", new_callable=AsyncMock):
                # Run the service
                run_service()
                
                # Verify logging was configured
                mock_configure_logging.assert_called_once()


def test_startup_logging_messages(caplog):
    """Test that startup information is logged."""
    # Set up logging to capture log messages
    caplog.set_level(logging.INFO)
    
    # Patch logging_config.configure_logging
    with patch("src.config.logging_config.configure_logging"):
        # Patch asyncio.get_event_loop
        with patch("asyncio.get_event_loop"):
            # Patch the main function to avoid actually running it
            with patch("src.main.main", new_callable=AsyncMock):
                # Run the service
                run_service()
                
                # Verify startup information was logged
                assert "Starting Document Service" in caplog.text
                assert "Python version" in caplog.text
                assert "Running in directory" in caplog.text