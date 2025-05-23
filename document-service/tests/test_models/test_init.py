#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the models package initialization.

This module contains tests to verify that the models package correctly imports and
re-exports all model components, providing a clean API surface for model imports
throughout the service.

These tests ensure that:
1. All components listed in __all__ are actually imported and available from the models package
2. The package structure is correctly maintained
3. All model components are properly exposed
4. Import paths work as expected
5. Backward compatibility is maintained
"""

import unittest
import importlib
import sys
from types import ModuleType


class TestModelsInit(unittest.TestCase):
    """Test case for the models package initialization."""

    def setUp(self):
        """Set up the test case by importing the models package."""
        # Import the models package
        self.models_module = importlib.import_module('src.models')

    def test_all_variable_exists(self):
        """Test that the __all__ variable exists in the models package."""
        self.assertTrue(hasattr(self.models_module, '__all__'))
        self.assertIsInstance(self.models_module.__all__, list)
        self.assertGreater(len(self.models_module.__all__), 0)

    def test_all_components_are_exported(self):
        """Test that all components listed in __all__ are actually exported."""
        for component_name in self.models_module.__all__:
            self.assertTrue(
                hasattr(self.models_module, component_name),
                f"Component '{component_name}' is listed in __all__ but not exported"
            )

    def test_base_model_is_exported(self):
        """Test that the BaseModel class is properly exported."""
        self.assertTrue(hasattr(self.models_module, 'BaseModel'))
        self.assertEqual(self.models_module.BaseModel.__name__, 'BaseModel')
        # Verify it's a class
        self.assertTrue(isinstance(self.models_module.BaseModel, type))

    def test_classifier_implementations_are_exported(self):
        """Test that classifier implementations are properly exported."""
        classifiers = ['SVMClassifier', 'RandomForestClassifier', 'DocumentClassifier']
        for classifier in classifiers:
            self.assertTrue(
                hasattr(self.models_module, classifier),
                f"Classifier '{classifier}' is not exported"
            )
            self.assertEqual(getattr(self.models_module, classifier).__name__, classifier)
            # Verify it's a class
            self.assertTrue(isinstance(getattr(self.models_module, classifier), type))

    def test_feature_extraction_utilities_are_exported(self):
        """Test that feature extraction utilities are properly exported."""
        utilities = [
            'TextExtractor',
            'TextPreprocessor',
            'TfidfFeatureExtractor',
            'MetadataFeatureExtractor',
            'DimensionalityReducer',
            'FeatureExtractor'
        ]
        for utility in utilities:
            self.assertTrue(
                hasattr(self.models_module, utility),
                f"Utility '{utility}' is not exported"
            )
            self.assertEqual(getattr(self.models_module, utility).__name__, utility)
            # Verify it's a class
            self.assertTrue(isinstance(getattr(self.models_module, utility), type))

    def test_model_serialization_functions_are_exported(self):
        """Test that model serialization functions are properly exported."""
        functions = [
            'save_model',
            'load_model',
            'list_models',
            'get_model_metadata',
            'register_model',
            'delete_model',
            'rollback_model',
            'validate_model'
        ]
        for function in functions:
            self.assertTrue(
                hasattr(self.models_module, function),
                f"Function '{function}' is not exported"
            )
            # Verify it's a function
            import types
            self.assertTrue(isinstance(getattr(self.models_module, function), types.FunctionType))

    def test_model_evaluation_components_are_exported(self):
        """Test that model evaluation components are properly exported."""
        components = [
            'ModelEvaluator',  # Class
            'plot_learning_curve',  # Function
            'plot_precision_recall_curve',  # Function
            'plot_calibration_curve',  # Function
            'evaluate_model_performance'  # Function
        ]
        for component in components:
            self.assertTrue(
                hasattr(self.models_module, component),
                f"Component '{component}' is not exported"
            )
            # Check if it's a class or function
            component_obj = getattr(self.models_module, component)
            if component.startswith('plot_') or component == 'evaluate_model_performance':
                import types
                self.assertTrue(isinstance(component_obj, types.FunctionType))
            else:
                self.assertTrue(isinstance(component_obj, type))

    def test_model_training_components_are_exported(self):
        """Test that model training components are properly exported."""
        components = [
            'ModelTrainer',  # Class
            'prepare_dataset',  # Function
            'optimize_hyperparameters',  # Function
            'train_model_with_cv'  # Function
        ]
        for component in components:
            self.assertTrue(
                hasattr(self.models_module, component),
                f"Component '{component}' is not exported"
            )
            # Check if it's a class or function
            component_obj = getattr(self.models_module, component)
            if component == 'ModelTrainer':
                self.assertTrue(isinstance(component_obj, type))
            else:
                import types
                self.assertTrue(isinstance(component_obj, types.FunctionType))

    def test_direct_imports_work(self):
        """Test that direct imports from the models package work as expected."""
        # This test verifies that users can import components directly from the models package
        # For example: from src.models import SVMClassifier
        import sys
        from unittest.mock import patch
        
        # Create a mock module to test imports
        mock_module = ModuleType('mock_module')
        sys.modules['mock_module'] = mock_module
        
        # Test importing a few representative components
        components_to_test = [
            'BaseModel',
            'SVMClassifier',
            'DocumentClassifier',
            'FeatureExtractor',
            'save_model',
            'ModelEvaluator',
            'prepare_dataset'
        ]
        
        for component in components_to_test:
            # Use exec to simulate: from src.models import {component}
            exec(f"from src.models import {component}")
            # Verify the component is imported correctly
            self.assertTrue(
                component in locals(),
                f"Failed to import {component} directly from models package"
            )
            # Verify it's the same object as in the models module
            self.assertIs(locals()[component], getattr(self.models_module, component))
        
        # Clean up
        del sys.modules['mock_module']

    def test_backward_compatibility(self):
        """Test backward compatibility of imports."""
        # This test ensures that any deprecated or renamed components are still available
        # for backward compatibility
        
        # Currently, there are no deprecated or renamed components in the models package
        # This test is a placeholder for future backward compatibility checks
        pass

    def test_import_all_components(self):
        """Test importing all components from the models package."""
        # This test verifies that users can import all components from the models package
        # For example: from src.models import *
        import sys
        from unittest.mock import patch
        
        # Create a mock module to test imports
        mock_module = ModuleType('mock_module')
        sys.modules['mock_module'] = mock_module
        
        # Use exec to simulate: from src.models import *
        exec("from src.models import *")
        
        # Verify all components in __all__ are imported
        for component in self.models_module.__all__:
            self.assertTrue(
                component in locals(),
                f"Failed to import {component} when using 'from src.models import *'"
            )
            # Verify it's the same object as in the models module
            self.assertIs(locals()[component], getattr(self.models_module, component))
        
        # Clean up
        del sys.modules['mock_module']

    def test_module_docstring(self):
        """Test that the models package has a proper docstring."""
        self.assertIsNotNone(self.models_module.__doc__)
        self.assertGreater(len(self.models_module.__doc__), 0)
        # Check that the docstring mentions key components
        docstring = self.models_module.__doc__
        self.assertIn("BaseModel", docstring)
        self.assertIn("SVMClassifier", docstring)
        self.assertIn("RandomForestClassifier", docstring)
        self.assertIn("DocumentClassifier", docstring)
        self.assertIn("Feature", docstring)  # Should mention feature extraction
        self.assertIn("save_model", docstring)  # Should mention serialization


if __name__ == '__main__':
    unittest.main()