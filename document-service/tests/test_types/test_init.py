#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the types package initialization in the Document Service.

This module validates that all type definitions are correctly exported and importable
throughout the application. These tests ensure a clean import interface and prevent
circular dependencies.
"""

import sys
import inspect
import importlib
from typing import get_type_hints, Any, Dict, List, Optional, Union, Generic, TypeVar

import pytest


def test_all_types_importable_from_package():
    """
    Test that all types can be imported directly from the types package.
    This ensures the __init__.py file correctly re-exports all types.
    """
    # Import the types package
    from document_service.types import (
        # From errors.py
        ServiceError,
        ErrorDetails,
        LogEntry,
        ErrorCategory,
        MonitoringAlert,
        Result,
        
        # From classification.py
        ClassificationModel,
        FeatureVector,
        ClassificationResult,
        ConfidenceScore,
        ModelParameters,
        ClassificationMetrics,
        
        # From storage.py
        S3ClientConfig,
        StorageOptions,
        StorageMetadata,
        BucketConfig,
        StorageResult,
        StorageKey,
        
        # From documents.py
        DocumentMetadata,
        DocumentContent,
        DocumentType,
        ProcessingStatus,
        DocumentSource,
        Document,
        
        # From messages.py
        MessagePayload,
        MessageHeaders,
        ExchangeConfig,
        QueueConfig,
        PublishOptions,
        ConsumeOptions,
        
        # From config.py
        ConfigDict,
        ServiceConfig,
        ModelConfig,
        RabbitMQConfig,
        S3Config,
        LoggingConfig,
    )
    
    # Assert that all types are defined
    assert ServiceError is not None
    assert ErrorDetails is not None
    assert LogEntry is not None
    assert ErrorCategory is not None
    assert MonitoringAlert is not None
    assert Result is not None
    
    assert ClassificationModel is not None
    assert FeatureVector is not None
    assert ClassificationResult is not None
    assert ConfidenceScore is not None
    assert ModelParameters is not None
    assert ClassificationMetrics is not None
    
    assert S3ClientConfig is not None
    assert StorageOptions is not None
    assert StorageMetadata is not None
    assert BucketConfig is not None
    assert StorageResult is not None
    assert StorageKey is not None
    
    assert DocumentMetadata is not None
    assert DocumentContent is not None
    assert DocumentType is not None
    assert ProcessingStatus is not None
    assert DocumentSource is not None
    assert Document is not None
    
    assert MessagePayload is not None
    assert MessageHeaders is not None
    assert ExchangeConfig is not None
    assert QueueConfig is not None
    assert PublishOptions is not None
    assert ConsumeOptions is not None
    
    assert ConfigDict is not None
    assert ServiceConfig is not None
    assert ModelConfig is not None
    assert RabbitMQConfig is not None
    assert S3Config is not None
    assert LoggingConfig is not None


def test_all_list_contains_all_exports():
    """
    Test that the __all__ list in __init__.py contains all exported types.
    This ensures that `from document_service.types import *` works correctly.
    """
    # Import the types package
    import document_service.src.types as types_package
    
    # Get the __all__ list
    all_list = types_package.__all__
    
    # Expected types from each module
    expected_types = [
        # From errors.py
        'ServiceError',
        'ErrorDetails',
        'LogEntry',
        'ErrorCategory',
        'MonitoringAlert',
        'Result',
        
        # From classification.py
        'ClassificationModel',
        'FeatureVector',
        'ClassificationResult',
        'ConfidenceScore',
        'ModelParameters',
        'ClassificationMetrics',
        
        # From storage.py
        'S3ClientConfig',
        'StorageOptions',
        'StorageMetadata',
        'BucketConfig',
        'StorageResult',
        'StorageKey',
        
        # From documents.py
        'DocumentMetadata',
        'DocumentContent',
        'DocumentType',
        'ProcessingStatus',
        'DocumentSource',
        'Document',
        
        # From messages.py
        'MessagePayload',
        'MessageHeaders',
        'ExchangeConfig',
        'QueueConfig',
        'PublishOptions',
        'ConsumeOptions',
        
        # From config.py
        'ConfigDict',
        'ServiceConfig',
        'ModelConfig',
        'RabbitMQConfig',
        'S3Config',
        'LoggingConfig',
    ]
    
    # Check that all expected types are in the __all__ list
    for type_name in expected_types:
        assert type_name in all_list, f"Type {type_name} is missing from __all__ list"
    
    # Check that there are no extra types in the __all__ list
    assert len(all_list) == len(expected_types), "__all__ list contains extra types"


def test_no_circular_imports():
    """
    Test that there are no circular imports in the types package.
    This ensures that the package can be imported without issues.
    """
    # Try importing each module individually to check for circular imports
    modules = [
        'document_service.types.errors',
        'document_service.types.classification',
        'document_service.types.storage',
        'document_service.types.documents',
        'document_service.types.messages',
        'document_service.types.config',
    ]
    
    for module_name in modules:
        # Import the module
        module = importlib.import_module(module_name)
        # If we get here without an exception, the import succeeded
        assert module is not None


def test_documentation_strings():
    """
    Test that the types package and its modules have proper documentation strings.
    This ensures that the code is well-documented.
    """
    # Import the types package
    import document_service.src.types as types_package
    
    # Check that the package has a docstring
    assert types_package.__doc__ is not None, "Types package is missing a docstring"
    assert len(types_package.__doc__) > 0, "Types package has an empty docstring"
    
    # Check that the docstring contains expected information
    docstring = types_package.__doc__.lower()
    assert "type" in docstring, "Docstring should mention 'type'"
    assert "import" in docstring, "Docstring should mention 'import'"
    
    # Check individual modules for docstrings
    modules = [
        'document_service.types.errors',
        'document_service.types.classification',
        'document_service.types.storage',
        'document_service.types.documents',
        'document_service.types.messages',
        'document_service.types.config',
    ]
    
    for module_name in modules:
        # Import the module
        module = importlib.import_module(module_name)
        # Check that the module has a docstring
        assert module.__doc__ is not None, f"Module {module_name} is missing a docstring"
        assert len(module.__doc__) > 0, f"Module {module_name} has an empty docstring"


def test_type_hints_present():
    """
    Test that all exported types have proper type hints.
    This ensures that static type checking works correctly.
    """
    # Import the types package
    import document_service.src.types as types_package
    
    # Get all exported types that are classes (not enums or type aliases)
    class_types = [
        'ServiceError',
        'ErrorDetails',
        'LogEntry',
        'MonitoringAlert',
        'Result',
        'ClassificationResult',
        'ModelParameters',
        'ClassificationMetrics',
        'S3ClientConfig',
        'StorageOptions',
        'StorageMetadata',
        'BucketConfig',
        'DocumentMetadata',
        'DocumentContent',
        'DocumentSource',
        'Document',
        'MessagePayload',
        'MessageHeaders',
        'ExchangeConfig',
        'QueueConfig',
        'PublishOptions',
        'ConsumeOptions',
        'ServiceConfig',
        'ModelConfig',
        'RabbitMQConfig',
        'S3Config',
        'LoggingConfig',
    ]
    
    for type_name in class_types:
        # Get the class
        cls = getattr(types_package, type_name)
        
        # Skip if it's not a class
        if not inspect.isclass(cls):
            continue
        
        # Get the type hints for the class
        try:
            hints = get_type_hints(cls)
            # Check that there are type hints
            assert len(hints) > 0, f"Class {type_name} has no type hints"
        except TypeError:
            # Some classes might not support get_type_hints
            pass


def test_relative_imports():
    """
    Test that relative imports within the package work correctly.
    This ensures that modules can import from each other without issues.
    """
    # Create a temporary module that uses relative imports
    import types
    test_module = types.ModuleType('test_relative_imports')
    test_module.__package__ = 'document_service.types'
    
    # Add the module to sys.modules
    sys.modules['document_service.types.test_relative_imports'] = test_module
    
    # Try relative imports
    exec("""
    from . import errors
    from . import classification
    from . import storage
    from . import documents
    from . import messages
    from . import config
    
    assert errors is not None
    assert classification is not None
    assert storage is not None
    assert documents is not None
    assert messages is not None
    assert config is not None
    """, test_module.__dict__)
    
    # Clean up
    del sys.modules['document_service.types.test_relative_imports']


def test_package_level_exports():
    """
    Test that all types are exported at the package level.
    This ensures that users can import directly from the package.
    """
    # Import the types package
    import document_service.types as types_package
    
    # Get all exported names
    exported_names = dir(types_package)
    
    # Check that all names in __all__ are exported
    for name in types_package.__all__:
        assert name in exported_names, f"Name {name} is in __all__ but not exported"


def test_import_star():
    """
    Test that `from document_service.types import *` works correctly.
    This ensures that the __all__ list is properly defined.
    """
    # Create a temporary module that uses import *
    import types
    test_module = types.ModuleType('test_import_star')
    
    # Add the module to sys.modules
    sys.modules['test_import_star'] = test_module
    
    # Try import *
    exec("""
    from document_service.types import *
    
    # Check that all types are imported
    assert ServiceError is not None
    assert ErrorDetails is not None
    assert LogEntry is not None
    assert ErrorCategory is not None
    assert MonitoringAlert is not None
    assert Result is not None
    
    assert ClassificationModel is not None
    assert FeatureVector is not None
    assert ClassificationResult is not None
    assert ConfidenceScore is not None
    assert ModelParameters is not None
    assert ClassificationMetrics is not None
    
    assert S3ClientConfig is not None
    assert StorageOptions is not None
    assert StorageMetadata is not None
    assert BucketConfig is not None
    assert StorageResult is not None
    assert StorageKey is not None
    
    assert DocumentMetadata is not None
    assert DocumentContent is not None
    assert DocumentType is not None
    assert ProcessingStatus is not None
    assert DocumentSource is not None
    assert Document is not None
    
    assert MessagePayload is not None
    assert MessageHeaders is not None
    assert ExchangeConfig is not None
    assert QueueConfig is not None
    assert PublishOptions is not None
    assert ConsumeOptions is not None
    
    assert ConfigDict is not None
    assert ServiceConfig is not None
    assert ModelConfig is not None
    assert RabbitMQConfig is not None
    assert S3Config is not None
    assert LoggingConfig is not None
    """, test_module.__dict__)
    
    # Clean up
    del sys.modules['test_import_star']


def test_type_consistency():
    """
    Test that types are consistent across imports.
    This ensures that importing a type directly from its module
    or from the package returns the same type.
    """
    # Import types from the package
    from document_service.types import ServiceError as PackageServiceError
    from document_service.types import DocumentMetadata as PackageDocumentMetadata
    from document_service.types import ClassificationResult as PackageClassificationResult
    
    # Import types directly from their modules
    from document_service.types.errors import ServiceError as ModuleServiceError
    from document_service.types.documents import DocumentMetadata as ModuleDocumentMetadata
    from document_service.types.classification import ClassificationResult as ModuleClassificationResult
    
    # Check that they are the same
    assert PackageServiceError is ModuleServiceError
    assert PackageDocumentMetadata is ModuleDocumentMetadata
    assert PackageClassificationResult is ModuleClassificationResult


def test_module_structure():
    """
    Test that the types package has the expected module structure.
    This ensures that all required modules are present.
    """
    # Import the types package
    import document_service.types as types_package
    
    # Check that all modules are present
    assert hasattr(types_package, 'errors'), "Module 'errors' is missing"
    assert hasattr(types_package, 'classification'), "Module 'classification' is missing"
    assert hasattr(types_package, 'storage'), "Module 'storage' is missing"
    assert hasattr(types_package, 'documents'), "Module 'documents' is missing"
    assert hasattr(types_package, 'messages'), "Module 'messages' is missing"
    assert hasattr(types_package, 'config'), "Module 'config' is missing"


def test_enum_values():
    """
    Test that enum types have the expected values.
    This ensures that enum types are correctly defined and exported.
    """
    # Import enum types
    from document_service.types import DocumentType, ProcessingStatus, ErrorCategory
    
    # Check DocumentType enum values
    assert hasattr(DocumentType, 'APPLICATION'), "DocumentType.APPLICATION is missing"
    assert hasattr(DocumentType, 'TAX_RETURN'), "DocumentType.TAX_RETURN is missing"
    assert hasattr(DocumentType, 'BANK_STATEMENT'), "DocumentType.BANK_STATEMENT is missing"
    assert hasattr(DocumentType, 'PAY_STUB'), "DocumentType.PAY_STUB is missing"
    assert hasattr(DocumentType, 'ID_DOCUMENT'), "DocumentType.ID_DOCUMENT is missing"
    assert hasattr(DocumentType, 'OTHER'), "DocumentType.OTHER is missing"
    
    # Check ProcessingStatus enum values
    assert hasattr(ProcessingStatus, 'RECEIVED'), "ProcessingStatus.RECEIVED is missing"
    assert hasattr(ProcessingStatus, 'CLASSIFYING'), "ProcessingStatus.CLASSIFYING is missing"
    assert hasattr(ProcessingStatus, 'CLASSIFIED'), "ProcessingStatus.CLASSIFIED is missing"
    assert hasattr(ProcessingStatus, 'EXTRACTING'), "ProcessingStatus.EXTRACTING is missing"
    assert hasattr(ProcessingStatus, 'EXTRACTED'), "ProcessingStatus.EXTRACTED is missing"
    assert hasattr(ProcessingStatus, 'FAILED'), "ProcessingStatus.FAILED is missing"
    assert hasattr(ProcessingStatus, 'COMPLETED'), "ProcessingStatus.COMPLETED is missing"
    
    # Check ErrorCategory enum values
    assert hasattr(ErrorCategory, 'VALIDATION'), "ErrorCategory.VALIDATION is missing"
    assert hasattr(ErrorCategory, 'PROCESSING'), "ErrorCategory.PROCESSING is missing"
    assert hasattr(ErrorCategory, 'STORAGE'), "ErrorCategory.STORAGE is missing"
    assert hasattr(ErrorCategory, 'MESSAGING'), "ErrorCategory.MESSAGING is missing"
    assert hasattr(ErrorCategory, 'CONFIGURATION'), "ErrorCategory.CONFIGURATION is missing"
    assert hasattr(ErrorCategory, 'AUTHENTICATION'), "ErrorCategory.AUTHENTICATION is missing"
    assert hasattr(ErrorCategory, 'AUTHORIZATION'), "ErrorCategory.AUTHORIZATION is missing"
    assert hasattr(ErrorCategory, 'EXTERNAL'), "ErrorCategory.EXTERNAL is missing"
    assert hasattr(ErrorCategory, 'UNKNOWN'), "ErrorCategory.UNKNOWN is missing"


def test_generic_types():
    """
    Test that generic types work correctly.
    This ensures that generic types like Result[T] can be used with different type parameters.
    """
    # Import the Result type
    from document_service.types import Result
    from typing import TypeVar, Dict, List, Optional
    
    # Define some type variables and types for testing
    T = TypeVar('T')
    
    # Test with different type parameters
    result_str = Result[str]
    result_int = Result[int]
    result_dict = Result[Dict[str, str]]
    result_list = Result[List[int]]
    result_optional = Result[Optional[str]]
    
    # Create instances of the generic types
    ok_str = result_str.ok("success")
    ok_int = result_int.ok(42)
    ok_dict = result_dict.ok({"key": "value"})
    ok_list = result_list.ok([1, 2, 3])
    ok_optional = result_optional.ok(None)
    
    # Check that the instances have the correct values
    assert ok_str.value == "success"
    assert ok_int.value == 42
    assert ok_dict.value == {"key": "value"}
    assert ok_list.value == [1, 2, 3]
    assert ok_optional.value is None
    
    # Check that all instances have success=True
    assert ok_str.success is True
    assert ok_int.success is True
    assert ok_dict.success is True
    assert ok_list.success is True
    assert ok_optional.success is True
    
    # Create error instances
    error_str = result_str.fail("error")
    error_int = result_int.fail("error")
    
    # Check that error instances have the correct values
    assert error_str.error == "error"
    assert error_int.error == "error"
    
    # Check that error instances have success=False
    assert error_str.success is False
    assert error_int.success is False


def test_type_annotations():
    """
    Test that type annotations are correctly defined.
    This ensures that static type checking works correctly.
    """
    # Import types with annotations
    from document_service.types import (
        DocumentMetadata,
        ClassificationResult,
        S3ClientConfig,
        MessagePayload,
        ServiceConfig
    )
    from typing import get_type_hints
    
    # Get type hints for DocumentMetadata
    doc_meta_hints = get_type_hints(DocumentMetadata)
    assert 'filename' in doc_meta_hints, "DocumentMetadata.filename type hint is missing"
    assert 'content_type' in doc_meta_hints, "DocumentMetadata.content_type type hint is missing"
    assert 'size' in doc_meta_hints, "DocumentMetadata.size type hint is missing"
    
    # Get type hints for ClassificationResult
    class_result_hints = get_type_hints(ClassificationResult)
    assert 'document_type' in class_result_hints, "ClassificationResult.document_type type hint is missing"
    assert 'confidence' in class_result_hints, "ClassificationResult.confidence type hint is missing"
    assert 'probabilities' in class_result_hints, "ClassificationResult.probabilities type hint is missing"
    
    # Get type hints for S3ClientConfig
    s3_config_hints = get_type_hints(S3ClientConfig)
    assert 'endpoint_url' in s3_config_hints, "S3ClientConfig.endpoint_url type hint is missing"
    assert 'region_name' in s3_config_hints, "S3ClientConfig.region_name type hint is missing"
    assert 'bucket_name' in s3_config_hints, "S3ClientConfig.bucket_name type hint is missing"
    
    # Get type hints for MessagePayload
    message_payload_hints = get_type_hints(MessagePayload)
    assert 'document_id' in message_payload_hints, "MessagePayload.document_id type hint is missing"
    assert 'action' in message_payload_hints, "MessagePayload.action type hint is missing"
    assert 'data' in message_payload_hints, "MessagePayload.data type hint is missing"
    
    # Get type hints for ServiceConfig
    service_config_hints = get_type_hints(ServiceConfig)
    assert 'name' in service_config_hints, "ServiceConfig.name type hint is missing"
    assert 'version' in service_config_hints, "ServiceConfig.version type hint is missing"
    assert 'port' in service_config_hints, "ServiceConfig.port type hint is missing"


def test_error_handling():
    """
    Test that error handling types work correctly.
    This ensures that error handling is consistent throughout the application.
    """
    # Import error handling types
    from document_service.types import ServiceError, ErrorDetails, Result
    
    # Create an error details instance
    error_details = ErrorDetails(
        message="Test error",
        code="TEST_ERROR",
        category="validation",
        context={"param": "value"},
        stack_trace="Traceback: ..."  # Simplified for testing
    )
    
    # Create a service error with the error details
    service_error = ServiceError(error_details)
    
    # Check that the service error has the correct details
    assert service_error.details == error_details
    assert str(service_error) == "Test error"
    
    # Test the Result type for error handling
    # Success case
    success_result = Result.ok("success value")
    assert success_result.success is True
    assert success_result.value == "success value"
    assert success_result.error is None
    
    # Error case
    error_result = Result.fail(service_error)
    assert error_result.success is False
    assert error_result.value is None
    assert error_result.error == service_error
    
    # Test error handling with different error types
    # Standard exception
    std_error_result = Result.fail(ValueError("Invalid value"))
    assert std_error_result.success is False
    assert std_error_result.error is not None
    assert isinstance(std_error_result.error, ValueError)
    
    # String error message
    str_error_result = Result.fail("Something went wrong")
    assert str_error_result.success is False
    assert str_error_result.error == "Something went wrong"