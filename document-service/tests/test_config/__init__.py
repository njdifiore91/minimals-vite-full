#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document Service Configuration Tests Package

This package contains unit tests for the Document Service configuration modules,
which are responsible for setting up and managing various aspects of the service:
- Application configuration (app_config.py)
- S3 storage configuration (s3_config.py)
- RabbitMQ messaging configuration (rabbitmq_config.py)
- Machine learning model configuration (model_config.py)
- Logging configuration (logging_config.py)

These tests ensure that configuration is correctly loaded from environment variables,
validated, and applied with appropriate defaults for different environments
(development, staging, production). They verify that the Document Service meets
the configuration requirements specified in the Merchant Cash Advance (MCA)
Application Processing System technical specification.
"""

__version__ = '0.1.0'
__author__ = 'Dollar Funding Engineering Team'
__maintainer__ = 'Dollar Funding Engineering Team'
__email__ = 'engineering@dollarfunding.com'
__status__ = 'Development'

# Make commonly used test utilities available at the package level
from pathlib import Path
import os
import sys

# Define the test_config directory for easy access to test resources
TEST_CONFIG_DIR = Path(__file__).parent.absolute()

# Define test constants that may be used across multiple test modules
TEST_ENVIRONMENTS = ['development', 'staging', 'production']
CONFIG_MODULES = ['app_config', 's3_config', 'rabbitmq_config', 'model_config', 'logging_config']

# Add the parent directory to sys.path to allow importing from the main package
# This enables test modules to import the actual configuration modules being tested
sys.path.insert(0, str(TEST_CONFIG_DIR.parent.parent))

# Import common test utilities if needed by multiple test modules
# This allows other test modules to import from tests.test_config directly