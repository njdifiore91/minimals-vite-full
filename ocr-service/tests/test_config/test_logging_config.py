#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the OCR Service's logging_config.py module.

These tests verify that logging configuration correctly sets up log levels,
formats, handlers, and context enrichment based on the environment.
They ensure that logging works correctly for monitoring, debugging, and troubleshooting.
"""

import os
import json
import logging
import pytest
from unittest.mock import patch, MagicMock, call
from typing import Dict, Any

# Import the module to test
from src.config.logging_config import (
    LOG_LEVELS,
    DEFAULT_LOG_LEVEL,
    LOG_FORMAT,
    DATE_FORMAT,
    ContextEnricher,
    JsonFormatter,
    set_request_context,
    clear_request_context,
    get_logging_config,
    configure_logging,
    get_logger
)


# ===== Test Constants and Default Values =====

def test_log_levels_constants():
    """
    Test that LOG_LEVELS contains the correct log levels for each environment.
    """
    assert "development" in LOG_LEVELS
    assert "staging" in LOG_LEVELS
    assert "production" in LOG_LEVELS
    
    assert LOG_LEVELS["development"] == logging.DEBUG
    assert LOG_LEVELS["staging"] == logging.INFO
    assert LOG_LEVELS["production"] == logging.INFO


def test_default_log_level():
    """
    Test that DEFAULT_LOG_LEVEL is set to INFO.
    """
    assert DEFAULT_LOG_LEVEL == logging.INFO


def test_log_format():
    """
    Test that LOG_FORMAT includes required fields.
    """
    assert "%(asctime)s" in LOG_FORMAT
    assert "%(levelname)s" in LOG_FORMAT
    assert "%(service)s" in LOG_FORMAT
    assert "%(request_id)s" in LOG_FORMAT
    assert "%(name)s" in LOG_FORMAT
    assert "%(message)s" in LOG_FORMAT


def test_date_format():
    """
    Test that DATE_FORMAT is correctly defined.
    """
    assert DATE_FORMAT == "%Y-%m-%d %H:%M:%S.%f"


# ===== Test ContextEnricher Class =====

def test_context_enricher_initialization():
    """
    Test that ContextEnricher can be initialized.
    """
    enricher = ContextEnricher()
    assert isinstance(enricher, logging.Filter)


@patch('src.config.logging_config.request_id_var')
@patch('src.config.logging_config.user_id_var')
@patch('src.config.logging_config.app_config')
def test_context_enricher_filter_with_context(mock_app_config, mock_user_id_var, mock_request_id_var):
    """
    Test that ContextEnricher.filter adds context information to log records when context is available.
    """
    # Setup mocks
    mock_request_id_var.get.return_value = 'test-request-id'
    mock_user_id_var.get.return_value = 'test-user-id'
    mock_app_config.__getitem__.side_effect = lambda key: {
        'service': {'name': 'ocr-service', 'version': '1.0.0'},
        'environment': 'development'
    }[key]
    
    # Create a log record
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test_file.py',
        lineno=42,
        msg='Test message',
        args=(),
        exc_info=None
    )
    
    # Apply the filter
    enricher = ContextEnricher()
    result = enricher.filter(record)
    
    # Verify the result
    assert result is True
    assert record.request_id == 'test-request-id'
    assert record.user_id == 'test-user-id'
    assert record.service == 'ocr-service-1.0.0'
    assert record.environment == 'development'


@patch('src.config.logging_config.request_id_var')
@patch('src.config.logging_config.user_id_var')
@patch('src.config.logging_config.app_config')
def test_context_enricher_filter_without_context(mock_app_config, mock_user_id_var, mock_request_id_var):
    """
    Test that ContextEnricher.filter adds default context information to log records when context is not available.
    """
    # Setup mocks
    mock_request_id_var.get.return_value = ''
    mock_user_id_var.get.return_value = ''
    mock_app_config.__getitem__.side_effect = lambda key: {
        'service': {'name': 'ocr-service', 'version': '1.0.0'},
        'environment': 'development'
    }[key]
    
    # Create a log record
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test_file.py',
        lineno=42,
        msg='Test message',
        args=(),
        exc_info=None
    )
    
    # Apply the filter
    enricher = ContextEnricher()
    result = enricher.filter(record)
    
    # Verify the result
    assert result is True
    assert record.request_id == 'no-request-id'
    assert record.user_id == 'no-user-id'
    assert record.service == 'ocr-service-1.0.0'
    assert record.environment == 'development'


# ===== Test JsonFormatter Class =====

def test_json_formatter_initialization():
    """
    Test that JsonFormatter can be initialized.
    """
    formatter = JsonFormatter()
    assert isinstance(formatter, logging.Formatter)


@patch('src.config.logging_config.app_config')
def test_json_formatter_format(mock_app_config):
    """
    Test that JsonFormatter.format correctly formats log records as JSON.
    """
    # Setup mocks
    mock_app_config.__getitem__.side_effect = lambda key: {
        'service': {'name': 'ocr-service', 'version': '1.0.0'},
        'environment': 'development'
    }[key]
    
    # Create a log record with context attributes
    record = logging.LogRecord(
        name='test_logger',
        level=logging.INFO,
        pathname='test_file.py',
        lineno=42,
        msg='Test message',
        args=(),
        exc_info=None
    )
    record.request_id = 'test-request-id'
    record.user_id = 'test-user-id'
    record.service = 'ocr-service-1.0.0'
    record.environment = 'development'
    record.custom_field = 'custom-value'
    
    # Format the record
    formatter = JsonFormatter()
    formatter.datefmt = DATE_FORMAT
    result = formatter.format(record)
    
    # Parse the JSON result
    json_result = json.loads(result)
    
    # Verify the result
    assert json_result['level'] == 'INFO'
    assert json_result['service'] == 'ocr-service-1.0.0'
    assert json_result['request_id'] == 'test-request-id'
    assert json_result['user_id'] == 'test-user-id'
    assert json_result['name'] == 'test_logger'
    assert json_result['message'] == 'Test message'
    assert json_result['environment'] == 'development'
    assert json_result['custom_field'] == 'custom-value'
    assert 'timestamp' in json_result


@patch('src.config.logging_config.app_config')
def test_json_formatter_format_with_exception(mock_app_config):
    """
    Test that JsonFormatter.format correctly formats log records with exceptions as JSON.
    """
    # Setup mocks
    mock_app_config.__getitem__.side_effect = lambda key: {
        'service': {'name': 'ocr-service', 'version': '1.0.0'},
        'environment': 'development'
    }[key]
    
    # Create an exception
    try:
        raise ValueError("Test exception")
    except ValueError as e:
        exc_info = (type(e), e, e.__traceback__)
    
    # Create a log record with an exception
    record = logging.LogRecord(
        name='test_logger',
        level=logging.ERROR,
        pathname='test_file.py',
        lineno=42,
        msg='Test exception',
        args=(),
        exc_info=exc_info
    )
    record.request_id = 'test-request-id'
    record.service = 'ocr-service-1.0.0'
    record.environment = 'development'
    
    # Format the record
    formatter = JsonFormatter()
    formatter.datefmt = DATE_FORMAT
    result = formatter.format(record)
    
    # Parse the JSON result
    json_result = json.loads(result)
    
    # Verify the result
    assert json_result['level'] == 'ERROR'
    assert json_result['service'] == 'ocr-service-1.0.0'
    assert json_result['request_id'] == 'test-request-id'
    assert json_result['name'] == 'test_logger'
    assert json_result['message'] == 'Test exception'
    assert json_result['environment'] == 'development'
    assert 'exception' in json_result
    assert 'ValueError: Test exception' in json_result['exception']


# ===== Test Request Context Functions =====

@patch('src.config.logging_config.request_id_var')
@patch('src.config.logging_config.user_id_var')
def test_set_request_context(mock_user_id_var, mock_request_id_var):
    """
    Test that set_request_context correctly sets the request context.
    """
    # Call the function
    set_request_context('test-request-id', 'test-user-id')
    
    # Verify that the context variables were set
    mock_request_id_var.set.assert_called_once_with('test-request-id')
    mock_user_id_var.set.assert_called_once_with('test-user-id')


@patch('src.config.logging_config.request_id_var')
@patch('src.config.logging_config.user_id_var')
def test_set_request_context_without_user_id(mock_user_id_var, mock_request_id_var):
    """
    Test that set_request_context correctly sets the request context without a user_id.
    """
    # Call the function
    set_request_context('test-request-id')
    
    # Verify that the request_id was set but user_id was not
    mock_request_id_var.set.assert_called_once_with('test-request-id')
    mock_user_id_var.set.assert_not_called()


@patch('src.config.logging_config.request_id_var')
@patch('src.config.logging_config.user_id_var')
def test_clear_request_context(mock_user_id_var, mock_request_id_var):
    """
    Test that clear_request_context correctly clears the request context.
    """
    # Call the function
    clear_request_context()
    
    # Verify that the context variables were cleared
    mock_request_id_var.set.assert_called_once_with('')
    mock_user_id_var.set.assert_called_once_with('')


# ===== Test Logging Configuration Functions =====

@patch('src.config.logging_config.app_config')
@patch('src.config.logging_config.os.makedirs')
def test_get_logging_config_development(mock_makedirs, mock_app_config):
    """
    Test that get_logging_config returns the correct configuration for development environment.
    """
    # Setup mocks
    mock_app_config.__getitem__.side_effect = lambda key: {
        'service': {'name': 'ocr-service', 'version': '1.0.0'},
        'environment': 'development'
    }[key]
    
    # Call the function
    config = get_logging_config()
    
    # Verify the result
    assert config['version'] == 1
    assert config['disable_existing_loggers'] is False
    
    # Verify formatters
    assert 'standard' in config['formatters']
    assert 'json' in config['formatters']
    assert config['formatters']['standard']['format'] == LOG_FORMAT
    assert config['formatters']['standard']['datefmt'] == DATE_FORMAT
    assert config['formatters']['json']['()'] == JsonFormatter
    
    # Verify filters
    assert 'context_enricher' in config['filters']
    assert config['filters']['context_enricher']['()'] == ContextEnricher
    
    # Verify handlers
    assert 'console' in config['handlers']
    assert config['handlers']['console']['level'] == logging.DEBUG
    assert config['handlers']['console']['formatter'] == 'standard'
    assert 'file' not in config['handlers']
    assert 'error_file' not in config['handlers']
    
    # Verify loggers
    assert '' in config['loggers']  # Root logger
    assert 'ocr-service' in config['loggers']
    assert config['loggers']['']['level'] == logging.DEBUG
    assert 'console' in config['loggers']['']['handlers']
    assert 'file' not in config['loggers']['']['handlers']
    assert 'error_file' not in config['loggers']['']['handlers']
    
    # Verify that the log directory was created
    mock_makedirs.assert_called_once()


@patch('src.config.logging_config.app_config')
@patch('src.config.logging_config.os.makedirs')
def test_get_logging_config_production(mock_makedirs, mock_app_config):
    """
    Test that get_logging_config returns the correct configuration for production environment.
    """
    # Setup mocks
    mock_app_config.__getitem__.side_effect = lambda key: {
        'service': {'name': 'ocr-service', 'version': '1.0.0'},
        'environment': 'production'
    }[key]
    
    # Call the function
    config = get_logging_config()
    
    # Verify the result
    assert config['version'] == 1
    assert config['disable_existing_loggers'] is False
    
    # Verify formatters
    assert 'standard' in config['formatters']
    assert 'json' in config['formatters']
    
    # Verify filters
    assert 'context_enricher' in config['filters']
    
    # Verify handlers
    assert 'console' in config['handlers']
    assert 'file' in config['handlers']
    assert 'error_file' in config['handlers']
    assert config['handlers']['console']['level'] == logging.INFO
    assert config['handlers']['console']['formatter'] == 'json'
    assert config['handlers']['file']['level'] == logging.INFO
    assert config['handlers']['file']['formatter'] == 'json'
    assert config['handlers']['error_file']['level'] == logging.ERROR
    assert config['handlers']['error_file']['formatter'] == 'json'
    
    # Verify loggers
    assert '' in config['loggers']  # Root logger
    assert 'ocr-service' in config['loggers']
    assert config['loggers']['']['level'] == logging.INFO
    assert 'console' in config['loggers']['']['handlers']
    assert 'file' in config['loggers']['']['handlers']
    assert 'error_file' in config['loggers']['']['handlers']
    
    # Verify that the log directory was created
    mock_makedirs.assert_called_once()


@patch('src.config.logging_config.app_config')
@patch('src.config.logging_config.os.makedirs')
def test_get_logging_config_staging(mock_makedirs, mock_app_config):
    """
    Test that get_logging_config returns the correct configuration for staging environment.
    """
    # Setup mocks
    mock_app_config.__getitem__.side_effect = lambda key: {
        'service': {'name': 'ocr-service', 'version': '1.0.0'},
        'environment': 'staging'
    }[key]
    
    # Call the function
    config = get_logging_config()
    
    # Verify the result
    assert config['version'] == 1
    assert config['disable_existing_loggers'] is False
    
    # Verify handlers
    assert 'console' in config['handlers']
    assert 'file' in config['handlers']
    assert 'error_file' in config['handlers']
    assert config['handlers']['console']['level'] == logging.INFO
    assert config['handlers']['file']['level'] == logging.INFO
    assert config['handlers']['error_file']['level'] == logging.ERROR
    
    # Verify loggers
    assert '' in config['loggers']  # Root logger
    assert 'ocr-service' in config['loggers']
    assert config['loggers']['']['level'] == logging.INFO
    assert 'console' in config['loggers']['']['handlers']
    assert 'file' in config['loggers']['']['handlers']
    assert 'error_file' in config['loggers']['']['handlers']
    
    # Verify that the log directory was created
    mock_makedirs.assert_called_once()


@patch('src.config.logging_config.app_config')
@patch('src.config.logging_config.os.makedirs')
def test_get_logging_config_unknown_environment(mock_makedirs, mock_app_config):
    """
    Test that get_logging_config uses DEFAULT_LOG_LEVEL for unknown environments.
    """
    # Setup mocks
    mock_app_config.__getitem__.side_effect = lambda key: {
        'service': {'name': 'ocr-service', 'version': '1.0.0'},
        'environment': 'unknown'
    }[key]
    
    # Call the function
    config = get_logging_config()
    
    # Verify the result
    assert config['loggers']['']['level'] == DEFAULT_LOG_LEVEL
    assert config['handlers']['console']['level'] == DEFAULT_LOG_LEVEL


@patch('src.config.logging_config.logging.config.dictConfig')
@patch('src.config.logging_config.get_logging_config')
@patch('src.config.logging_config.logging.getLogger')
def test_configure_logging_success(mock_get_logger, mock_get_logging_config, mock_dict_config):
    """
    Test that configure_logging correctly configures logging when successful.
    """
    # Setup mocks
    mock_config = {'version': 1, 'disable_existing_loggers': False}
    mock_get_logging_config.return_value = mock_config
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    
    # Call the function
    configure_logging()
    
    # Verify that logging was configured correctly
    mock_get_logging_config.assert_called_once()
    mock_dict_config.assert_called_once_with(mock_config)
    mock_get_logger.assert_called_once_with('ocr-service')
    mock_logger.info.assert_called_once()


@patch('src.config.logging_config.logging.config.dictConfig')
@patch('src.config.logging_config.get_logging_config')
@patch('src.config.logging_config.logging.basicConfig')
@patch('src.config.logging_config.logging.getLogger')
def test_configure_logging_failure(mock_get_logger, mock_basic_config, mock_get_logging_config, mock_dict_config):
    """
    Test that configure_logging falls back to basicConfig when dictConfig fails.
    """
    # Setup mocks
    mock_get_logging_config.return_value = {}
    mock_dict_config.side_effect = Exception("Test exception")
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    
    # Call the function
    configure_logging()
    
    # Verify that basic logging was configured as a fallback
    mock_get_logging_config.assert_called_once()
    mock_dict_config.assert_called_once()
    mock_basic_config.assert_called_once()
    mock_get_logger.assert_called_once_with('ocr-service')
    mock_logger.error.assert_called_once()


def test_get_logger():
    """
    Test that get_logger returns a logger with the specified name.
    """
    # Call the function
    logger = get_logger('test_logger')
    
    # Verify the result
    assert isinstance(logger, logging.Logger)
    assert logger.name == 'test_logger'


# ===== Integration Tests with Fixtures =====

@patch('src.config.logging_config.app_config')
def test_logging_config_with_dev_environment(mock_app_config, dev_env_vars):
    """
    Test that logging configuration is correct for development environment.
    """
    # Setup mocks
    mock_app_config.__getitem__.side_effect = lambda key: {
        'service': {'name': 'ocr-service', 'version': '1.0.0'},
        'environment': dev_env_vars['ENVIRONMENT']
    }[key]
    
    # Get the logging configuration
    config = get_logging_config()
    
    # Verify the configuration
    assert config['loggers']['']['level'] == logging.DEBUG
    assert config['handlers']['console']['formatter'] == 'standard'
    assert 'file' not in config['handlers']


@patch('src.config.logging_config.app_config')
def test_logging_config_with_staging_environment(mock_app_config, staging_env_vars):
    """
    Test that logging configuration is correct for staging environment.
    """
    # Setup mocks
    mock_app_config.__getitem__.side_effect = lambda key: {
        'service': {'name': 'ocr-service', 'version': '1.0.0'},
        'environment': staging_env_vars['ENVIRONMENT']
    }[key]
    
    # Get the logging configuration
    config = get_logging_config()
    
    # Verify the configuration
    assert config['loggers']['']['level'] == logging.INFO
    assert config['handlers']['console']['formatter'] == 'json'
    assert 'file' in config['handlers']
    assert 'error_file' in config['handlers']


@patch('src.config.logging_config.app_config')
def test_logging_config_with_prod_environment(mock_app_config, prod_env_vars):
    """
    Test that logging configuration is correct for production environment.
    """
    # Setup mocks
    mock_app_config.__getitem__.side_effect = lambda key: {
        'service': {'name': 'ocr-service', 'version': '1.0.0'},
        'environment': prod_env_vars['ENVIRONMENT']
    }[key]
    
    # Get the logging configuration
    config = get_logging_config()
    
    # Verify the configuration
    assert config['loggers']['']['level'] == logging.INFO
    assert config['handlers']['console']['formatter'] == 'json'
    assert 'file' in config['handlers']
    assert 'error_file' in config['handlers']


@patch('src.config.logging_config.logging')
@patch('src.config.logging_config.app_config')
def test_logging_integration_with_mock_app_config(mock_app_config, mock_logging, mock_logging_config):
    """
    Test that logging configuration integrates correctly with app_config.
    """
    # Setup mocks
    mock_app_config.__getitem__.side_effect = lambda key: {
        'service': {'name': mock_logging_config['level'], 'version': '1.0.0'},
        'environment': 'development'
    }[key]
    
    # Configure logging
    configure_logging()
    
    # Verify that logging was configured
    assert mock_logging.config.dictConfig.called


@patch('src.config.logging_config.request_id_var')
@patch('src.config.logging_config.user_id_var')
def test_request_context_integration(mock_user_id_var, mock_request_id_var):
    """
    Test that request context functions integrate correctly with logging.
    """
    # Set request context
    set_request_context('test-request-id', 'test-user-id')
    
    # Verify that context was set
    mock_request_id_var.set.assert_called_once_with('test-request-id')
    mock_user_id_var.set.assert_called_once_with('test-user-id')
    
    # Clear request context
    clear_request_context()
    
    # Verify that context was cleared
    assert mock_request_id_var.set.call_count == 2
    assert mock_user_id_var.set.call_count == 2
    mock_request_id_var.set.assert_called_with('')
    mock_user_id_var.set.assert_called_with('')