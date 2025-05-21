#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the logging utilities module.

This module contains tests for the logging_utils module, verifying that
the logging utilities work as expected and demonstrating their usage.
"""

import json
import logging
import sys
from io import StringIO
from unittest import TestCase, main

# Import the logging utilities to test
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.logging_utils import (
    configure_logger,
    get_logger,
    log_exception,
    log_with_context,
    set_request_id,
    get_request_id,
    clear_request_id,
    request_context,
    log_function_call,
    log_execution_time,
    log_critical_error,
)


class TestLoggingUtils(TestCase):
    """Test case for the logging utilities module."""

    def setUp(self):
        """Set up the test case."""
        # Capture log output
        self.log_output = StringIO()
        self.handler = logging.StreamHandler(self.log_output)
        self.logger = configure_logger(
            "test_logger",
            level="DEBUG",
            json_format=True,
            console_output=False,
        )
        self.logger.logger.addHandler(self.handler)

        # Clear any existing request ID
        clear_request_id()

    def tearDown(self):
        """Clean up after the test case."""
        # Remove the handler and close the output stream
        self.logger.logger.removeHandler(self.handler)
        self.log_output.close()

        # Clear any request ID set during the test
        clear_request_id()

    def test_basic_logging(self):
        """Test basic logging functionality."""
        # Log a message
        self.logger.info("Test message")

        # Get the log output
        log_output = self.log_output.getvalue()

        # Parse the JSON log entry
        log_entry = json.loads(log_output)

        # Verify the log entry
        self.assertEqual(log_entry["level"], "INFO")
        self.assertEqual(log_entry["message"], "Test message")
        self.assertEqual(log_entry["logger"], "test_logger")
        self.assertEqual(log_entry["service"], "ocr-service")

    def test_request_id_tracking(self):
        """Test request ID tracking."""
        # Set a request ID
        request_id = set_request_id("test-request-id")

        # Verify the request ID was set
        self.assertEqual(request_id, "test-request-id")
        self.assertEqual(get_request_id(), "test-request-id")

        # Log a message
        self.logger.info("Test message with request ID")

        # Get the log output
        log_output = self.log_output.getvalue()

        # Parse the JSON log entry
        log_entry = json.loads(log_output)

        # Verify the request ID is in the log entry
        self.assertEqual(log_entry["request_id"], "test-request-id")

        # Clear the request ID
        clear_request_id()

        # Verify the request ID was cleared
        self.assertIsNone(get_request_id())

    def test_request_context_manager(self):
        """Test the request context manager."""
        # Use the request context manager
        with request_context("context-manager-id"):
            # Verify the request ID was set
            self.assertEqual(get_request_id(), "context-manager-id")

            # Log a message
            self.logger.info("Test message with context manager")

        # Verify the request ID was cleared
        self.assertIsNone(get_request_id())

        # Get the log output
        log_output = self.log_output.getvalue()

        # Parse the JSON log entry
        log_entry = json.loads(log_output)

        # Verify the request ID is in the log entry
        self.assertEqual(log_entry["request_id"], "context-manager-id")

    def test_log_with_context(self):
        """Test logging with additional context."""
        # Log a message with context
        log_with_context(
            self.logger,
            logging.INFO,
            "Test message with context",
            {"test_key": "test_value"},
        )

        # Get the log output
        log_output = self.log_output.getvalue()

        # Parse the JSON log entry
        log_entry = json.loads(log_output)

        # Verify the context is in the log entry
        self.assertEqual(log_entry["test_key"], "test_value")

    def test_log_exception(self):
        """Test logging an exception."""
        try:
            # Raise an exception
            raise ValueError("Test exception")
        except ValueError:
            # Log the exception
            log_exception(self.logger, "An error occurred")

        # Get the log output
        log_output = self.log_output.getvalue()

        # Parse the JSON log entry
        log_entry = json.loads(log_output)

        # Verify the exception is in the log entry
        self.assertEqual(log_entry["level"], "ERROR")
        self.assertEqual(log_entry["message"], "An error occurred")
        self.assertEqual(log_entry["exception_type"], "ValueError")
        self.assertEqual(log_entry["exception_message"], "Test exception")
        self.assertIn("exception", log_entry)
        self.assertEqual(log_entry["exception"]["type"], "ValueError")
        self.assertEqual(log_entry["exception"]["message"], "Test exception")

    def test_log_function_call_decorator(self):
        """Test the log_function_call decorator."""

        @log_function_call(self.logger)
        def test_function(arg1, arg2=None):
            """Test function for the decorator."""
            return f"{arg1}-{arg2}"

        # Call the decorated function
        result = test_function("value1", arg2="value2")

        # Verify the function returned the expected result
        self.assertEqual(result, "value1-value2")

        # Get the log output
        log_output = self.log_output.getvalue()

        # Split the log output into lines
        log_lines = log_output.strip().split("\n")

        # Parse the JSON log entries
        log_entries = [json.loads(line) for line in log_lines]

        # Verify the function call was logged
        self.assertEqual(len(log_entries), 2)  # Two log entries: call and return
        self.assertIn("Calling", log_entries[0]["message"])
        self.assertIn("returned", log_entries[1]["message"])
        self.assertEqual(log_entries[0]["function_call"]["name"], "test_function")
        self.assertEqual(log_entries[1]["function_return"]["name"], "test_function")
        self.assertEqual(log_entries[1]["function_return"]["result"], "value1-value2")

    def test_log_execution_time_decorator(self):
        """Test the log_execution_time decorator."""

        @log_execution_time(self.logger)
        def test_function():
            """Test function for the decorator."""
            return "result"

        # Call the decorated function
        result = test_function()

        # Verify the function returned the expected result
        self.assertEqual(result, "result")

        # Get the log output
        log_output = self.log_output.getvalue()

        # Parse the JSON log entry
        log_entry = json.loads(log_output)

        # Verify the execution time was logged
        self.assertIn("executed in", log_entry["message"])
        self.assertIn("execution_time", log_entry)
        self.assertEqual(log_entry["execution_time"]["name"], "test_function")
        self.assertIsInstance(log_entry["execution_time"]["seconds"], float)

    def test_log_critical_error(self):
        """Test logging a critical error."""
        # Log a critical error
        log_critical_error(self.logger, "A critical error occurred")

        # Get the log output
        log_output = self.log_output.getvalue()

        # Parse the JSON log entry
        log_entry = json.loads(log_output)

        # Verify the critical error was logged
        self.assertEqual(log_entry["level"], "CRITICAL")
        self.assertEqual(log_entry["message"], "A critical error occurred")
        self.assertTrue(log_entry["alert"])
        self.assertIn("stack_trace", log_entry)


if __name__ == "__main__":
    main()