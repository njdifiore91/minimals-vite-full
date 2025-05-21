#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the models package initialization.

These tests verify that the models package correctly imports and re-exports
all model components, providing a clean API surface for model imports throughout
the service.
"""

import importlib
import inspect
import sys
from unittest import mock

import pytest


def test_all_variable_contains_expected_exports():
    """
    Test that the __all__ variable in models/__init__.py contains all expected exports.
    
    This ensures that the package's public API is correctly defined and maintained.
    """
    # Import the models package
    from document_service.models import __all__
    
    # Define the expected exports
    expected_exports = [
        # Base model
        'BaseModel',
        
        # Classifier implementations
        'SVMClassifier',
        'RandomForestClassifier',
        'DocumentClassifier',
        
        # Model serialization
        'save_model',
        'load_model',
        
        # Model evaluation
        'evaluate_classifier',
        'calculate_metrics',
        'plot_confusion_matrix',
        
        # Model training
        'train_model',
        'optimize_hyperparameters',
        'cross_validate',
        
        # Feature extraction
        'extract_document_features',
        'extract_text_features',
        'extract_metadata_features',
    ]
    
    # Check that all expected exports are in __all__
    for export in expected_exports:
        assert export in __all__, f"Expected export '{export}' not found in __all__"
    
    # Check that __all__ doesn't contain any unexpected exports
    assert len(__all__) == len(expected_exports), f"__all__ contains unexpected exports: {set(__all__) - set(expected_exports)}"


def test_all_exports_are_importable():
    """
    Test that all exports listed in __all__ can be imported from the models package.
    
    This ensures that the package correctly re-exports all components and that
    they can be imported using the package's public API.
    """
    # Import the models package
    import document_service.models as models
    
    # Check that all exports in __all__ are attributes of the models package
    for export in models.__all__:
        assert hasattr(models, export), f"Export '{export}' is listed in __all__ but not importable from models package"


def test_base_model_is_exported():
    """
    Test that the BaseModel class is correctly exported from the models package.
    
    This ensures that the base model interface is available for use throughout the service.
    """
    # Import the BaseModel from the models package
    from document_service.models import BaseModel
    
    # Check that it's a class
    assert inspect.isclass(BaseModel), "BaseModel is not a class"
    
    # Check that it has the expected methods
    expected_methods = ['fit', 'predict', 'predict_proba', 'evaluate']
    for method in expected_methods:
        assert hasattr(BaseModel, method), f"BaseModel is missing expected method '{method}'"


def test_classifier_implementations_are_exported():
    """
    Test that the classifier implementations are correctly exported from the models package.
    
    This ensures that the SVM and Random Forest classifiers, as well as the main
    DocumentClassifier, are available for use throughout the service.
    """
    # Import the classifier implementations from the models package
    from document_service.models import SVMClassifier, RandomForestClassifier, DocumentClassifier
    
    # Check that they're classes
    assert inspect.isclass(SVMClassifier), "SVMClassifier is not a class"
    assert inspect.isclass(RandomForestClassifier), "RandomForestClassifier is not a class"
    assert inspect.isclass(DocumentClassifier), "DocumentClassifier is not a class"
    
    # Check that the specific classifiers inherit from BaseModel
    from document_service.models import BaseModel
    assert issubclass(SVMClassifier, BaseModel), "SVMClassifier does not inherit from BaseModel"
    assert issubclass(RandomForestClassifier, BaseModel), "RandomForestClassifier does not inherit from BaseModel"


def test_model_utility_functions_are_exported():
    """
    Test that the model utility functions are correctly exported from the models package.
    
    This ensures that the serialization, evaluation, training, and feature extraction
    utilities are available for use throughout the service.
    """
    # Import the utility functions from the models package
    from document_service.models import (
        save_model, load_model,
        evaluate_classifier, calculate_metrics, plot_confusion_matrix,
        train_model, optimize_hyperparameters, cross_validate,
        extract_document_features, extract_text_features, extract_metadata_features
    )
    
    # Check that they're functions
    utility_functions = [
        save_model, load_model,
        evaluate_classifier, calculate_metrics, plot_confusion_matrix,
        train_model, optimize_hyperparameters, cross_validate,
        extract_document_features, extract_text_features, extract_metadata_features
    ]
    
    for func in utility_functions:
        assert callable(func), f"{func.__name__} is not callable"


def test_backward_compatibility_of_imports():
    """
    Test that the package maintains backward compatibility for imports.
    
    This ensures that code using older import patterns will continue to work
    with the current package structure.
    """
    # Define a list of import statements that should work
    import_statements = [
        "from document_service.models import BaseModel",
        "from document_service.models import SVMClassifier",
        "from document_service.models import RandomForestClassifier",
        "from document_service.models import DocumentClassifier",
        "from document_service.models import save_model, load_model",
        "from document_service.models import evaluate_classifier, calculate_metrics, plot_confusion_matrix",
        "from document_service.models import train_model, optimize_hyperparameters, cross_validate",
        "from document_service.models import extract_document_features, extract_text_features, extract_metadata_features",
    ]
    
    # Try to execute each import statement
    for import_statement in import_statements:
        try:
            exec(import_statement)
        except ImportError as e:
            pytest.fail(f"Import statement '{import_statement}' failed: {e}")


def test_module_structure_integrity():
    """
    Test that the module structure is intact and all expected modules are present.
    
    This ensures that the package structure is maintained and that all required
    modules are available.
    """
    # Define the expected modules
    expected_modules = [
        'document_service.models.base_model',
        'document_service.models.svm_classifier',
        'document_service.models.random_forest_classifier',
        'document_service.models.document_classifier',
        'document_service.models.model_serialization',
        'document_service.models.model_evaluation',
        'document_service.models.model_training',
        'document_service.models.feature_extraction',
    ]
    
    # Check that all expected modules can be imported
    for module_name in expected_modules:
        try:
            importlib.import_module(module_name)
        except ImportError as e:
            pytest.fail(f"Expected module '{module_name}' could not be imported: {e}")


def test_import_paths_are_clean():
    """
    Test that the import paths are clean and don't contain any unexpected side effects.
    
    This ensures that importing the models package doesn't have any unintended
    consequences, such as importing unnecessary modules or executing code that
    shouldn't be executed during import.
    """
    # Mock sys.modules to track which modules are imported
    original_modules = set(sys.modules.keys())
    
    # Import the models package
    importlib.import_module('document_service.models')
    
    # Check which new modules were imported
    new_modules = set(sys.modules.keys()) - original_modules
    
    # Define the expected modules that should be imported
    expected_modules = {
        'document_service.models',
        'document_service.models.base_model',
        'document_service.models.svm_classifier',
        'document_service.models.random_forest_classifier',
        'document_service.models.document_classifier',
        'document_service.models.model_serialization',
        'document_service.models.model_evaluation',
        'document_service.models.model_training',
        'document_service.models.feature_extraction',
    }
    
    # Check that only the expected modules were imported
    unexpected_modules = [m for m in new_modules if m.startswith('document_service.models') and m not in expected_modules]
    assert not unexpected_modules, f"Unexpected modules were imported: {unexpected_modules}"


def test_no_side_effects_during_import():
    """
    Test that importing the models package doesn't have any side effects.
    
    This ensures that the package doesn't execute any code that could have
    side effects, such as creating files, making network requests, or
    modifying global state.
    """
    # Create mock objects for functions that could have side effects
    with mock.patch('builtins.open') as mock_open, \
         mock.patch('os.path.exists') as mock_exists, \
         mock.patch('os.makedirs') as mock_makedirs:
        
        # Import the models package
        importlib.reload(importlib.import_module('document_service.models'))
        
        # Check that no files were opened or created
        mock_open.assert_not_called()
        mock_exists.assert_not_called()
        mock_makedirs.assert_not_called()


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])