#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for model serialization utilities.

This module contains tests for the model_serialization.py module, which provides
functions for saving, loading, and managing trained document classification models.
Tests verify that the serialization module correctly handles model serialization,
versioning, metadata storage, and model registry management.
"""

import os
import json
import pickle
import hashlib
import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest
import numpy as np
import joblib
from sklearn.base import BaseEstimator

# Fix the import path for tests
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from models.model_serialization import (
    save_model,
    load_model,
    list_models,
    get_model_metadata,
    register_model,
    delete_model,
    rollback_model,
    validate_model,
    _calculate_file_hash,
    _load_model_registry,
    _save_model_registry,
    _get_latest_model_version,
    _get_active_model_version
)


# Test save_model function
class TestSaveModel:
    """Tests for the save_model function."""

    def test_save_model_success(self, trained_svm_classifier, temp_model_path, model_metadata, monkeypatch):
        """Test successful model saving."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Mock register_model to avoid dependency
        with patch('models.model_serialization.register_model') as mock_register:
            model_name = "test_model"
            model_version = "1.0.0"
            
            # Call save_model
            result = save_model(
                model=trained_svm_classifier,
                model_name=model_name,
                model_version=model_version,
                metadata=model_metadata
            )
            
            # Check that files were created
            model_filename = f"{model_name}_{model_version}.joblib"
            metadata_filename = f"{model_name}_{model_version}.meta.json"
            hash_filename = f"{model_name}_{model_version}.sha256"
            
            assert (temp_model_path / model_filename).exists()
            assert (temp_model_path / metadata_filename).exists()
            assert (temp_model_path / hash_filename).exists()
            
            # Check that register_model was called
            mock_register.assert_called_once()
            
            # Check that the function returned the correct path
            assert result == str(temp_model_path / model_filename)
    
    def test_save_model_invalid_inputs(self, trained_svm_classifier, model_metadata):
        """Test save_model with invalid inputs."""
        # Test with empty model_name
        with pytest.raises(ValueError, match="Model name and version must be provided"):
            save_model(
                model=trained_svm_classifier,
                model_name="",
                model_version="1.0.0",
                metadata=model_metadata
            )
        
        # Test with empty model_version
        with pytest.raises(ValueError, match="Model name and version must be provided"):
            save_model(
                model=trained_svm_classifier,
                model_name="test_model",
                model_version="",
                metadata=model_metadata
            )
        
        # Test with non-estimator model
        with pytest.raises(ValueError, match="Model must be a scikit-learn estimator"):
            save_model(
                model={"not_a_model": True},
                model_name="test_model",
                model_version="1.0.0",
                metadata=model_metadata
            )
    
    def test_save_model_io_error(self, trained_svm_classifier, temp_model_path, model_metadata, monkeypatch):
        """Test save_model handling of IO errors."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Mock joblib.dump to raise an exception
        with patch('joblib.dump', side_effect=IOError("Mock IO error")):
            with pytest.raises(IOError, match="Mock IO error"):
                save_model(
                    model=trained_svm_classifier,
                    model_name="test_model",
                    model_version="1.0.0",
                    metadata=model_metadata
                )
    
    def test_save_model_enhanced_metadata(self, trained_svm_classifier, temp_model_path, model_metadata, monkeypatch):
        """Test that metadata is enhanced with additional information."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Mock register_model to capture metadata
        with patch('models.model_serialization.register_model') as mock_register:
            model_name = "test_model"
            model_version = "1.0.0"
            
            # Call save_model
            save_model(
                model=trained_svm_classifier,
                model_name=model_name,
                model_version=model_version,
                metadata=model_metadata
            )
            
            # Get the enhanced metadata from the register_model call
            _, _, _, enhanced_metadata = mock_register.call_args[0]
            
            # Check that additional fields were added
            assert "model_name" in enhanced_metadata
            assert "model_version" in enhanced_metadata
            assert "created_at" in enhanced_metadata
            assert "scikit_learn_version" in enhanced_metadata
            assert "python_version" in enhanced_metadata
            assert "environment" in enhanced_metadata
            
            # Check that original metadata was preserved
            for key, value in model_metadata.items():
                assert enhanced_metadata[key] == value


# Test load_model function
class TestLoadModel:
    """Tests for the load_model function."""

    def test_load_model_success(self, trained_svm_classifier, temp_model_path, model_metadata, monkeypatch):
        """Test successful model loading."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Save a model first
        with patch('models.model_serialization.register_model'):
            model_name = "test_model"
            model_version = "1.0.0"
            
            save_model(
                model=trained_svm_classifier,
                model_name=model_name,
                model_version=model_version,
                metadata=model_metadata
            )
        
        # Now load the model
        loaded_model, loaded_metadata = load_model(model_name, model_version)
        
        # Check that the model was loaded correctly
        assert isinstance(loaded_model, BaseEstimator)
        
        # Check that metadata was loaded correctly
        assert loaded_metadata["model_name"] == model_name
        assert loaded_metadata["model_version"] == model_version
        
        # Check that original metadata was preserved
        for key, value in model_metadata.items():
            assert loaded_metadata[key] == value
    
    def test_load_model_latest_version(self, trained_svm_classifier, temp_model_path, model_metadata, monkeypatch):
        """Test loading the latest model version when version is not specified."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Save multiple model versions
        with patch('models.model_serialization.register_model'):
            model_name = "test_model"
            
            # Save version 1.0.0
            save_model(
                model=trained_svm_classifier,
                model_name=model_name,
                model_version="1.0.0",
                metadata=model_metadata
            )
            
            # Save version 1.1.0
            save_model(
                model=trained_svm_classifier,
                model_name=model_name,
                model_version="1.1.0",
                metadata=model_metadata
            )
            
            # Save version 2.0.0
            save_model(
                model=trained_svm_classifier,
                model_name=model_name,
                model_version="2.0.0",
                metadata=model_metadata
            )
        
        # Mock _get_latest_model_version to return the latest version
        with patch('models.model_serialization._get_latest_model_version', return_value="2.0.0"):
            # Load the model without specifying a version
            loaded_model, loaded_metadata = load_model(model_name)
            
            # Check that the latest version was loaded
            assert loaded_metadata["model_version"] == "2.0.0"
    
    def test_load_model_file_not_found(self, temp_model_path, monkeypatch):
        """Test load_model when the model file doesn't exist."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Mock _get_latest_model_version to return a version
        with patch('models.model_serialization._get_latest_model_version', return_value="1.0.0"):
            # Try to load a non-existent model
            with pytest.raises(FileNotFoundError, match="Model file not found"):
                load_model("non_existent_model", "1.0.0")
    
    def test_load_model_integrity_check(self, trained_svm_classifier, temp_model_path, model_metadata, monkeypatch):
        """Test model integrity check during loading."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Save a model first
        with patch('models.model_serialization.register_model'):
            model_name = "test_model"
            model_version = "1.0.0"
            
            save_model(
                model=trained_svm_classifier,
                model_name=model_name,
                model_version=model_version,
                metadata=model_metadata
            )
        
        # Tamper with the model file to change its hash
        model_filepath = temp_model_path / f"{model_name}_{model_version}.joblib"
        with open(model_filepath, 'ab') as f:
            f.write(b'tampered')
        
        # Try to load the model with integrity check
        with pytest.raises(ValueError, match="Model integrity check failed"):
            load_model(model_name, model_version)
    
    def test_load_model_no_metadata(self, trained_svm_classifier, temp_model_path, monkeypatch):
        """Test loading a model when metadata file doesn't exist."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        model_name = "test_model"
        model_version = "1.0.0"
        
        # Save the model file directly without metadata
        model_filepath = temp_model_path / f"{model_name}_{model_version}.joblib"
        joblib.dump(trained_svm_classifier, model_filepath)
        
        # Create hash file
        hash_filepath = temp_model_path / f"{model_name}_{model_version}.sha256"
        with open(hash_filepath, 'w') as f:
            f.write(_calculate_file_hash(model_filepath))
        
        # Load the model
        with patch('models.model_serialization.validate_model', return_value=True):
            loaded_model, loaded_metadata = load_model(model_name, model_version)
            
            # Check that default metadata was created
            assert loaded_metadata["model_name"] == model_name
            assert loaded_metadata["model_version"] == model_version


# Test list_models function
class TestListModels:
    """Tests for the list_models function."""

    def test_list_models_empty(self, monkeypatch):
        """Test listing models when registry is empty."""
        # Mock _load_model_registry to return empty registry
        with patch('models.model_serialization._load_model_registry', return_value={}):
            models = list_models()
            assert len(models) == 0
    
    def test_list_models_with_entries(self, monkeypatch):
        """Test listing models when registry has entries."""
        # Create mock registry with entries
        mock_registry = {
            "model1_1.0.0": {"model_name": "model1", "model_version": "1.0.0"},
            "model2_1.0.0": {"model_name": "model2", "model_version": "1.0.0"},
            "model1_2.0.0": {"model_name": "model1", "model_version": "2.0.0"}
        }
        
        # Mock _load_model_registry to return the mock registry
        with patch('models.model_serialization._load_model_registry', return_value=mock_registry):
            models = list_models()
            
            # Check that all entries were returned
            assert len(models) == 3
            
            # Check that entries contain the expected data
            model_names = [model["model_name"] for model in models]
            assert "model1" in model_names
            assert "model2" in model_names
            
            model_versions = [model["model_version"] for model in models]
            assert "1.0.0" in model_versions
            assert "2.0.0" in model_versions


# Test get_model_metadata function
class TestGetModelMetadata:
    """Tests for the get_model_metadata function."""

    def test_get_model_metadata_success(self, trained_svm_classifier, temp_model_path, model_metadata, monkeypatch):
        """Test successful metadata retrieval."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Save a model first
        with patch('models.model_serialization.register_model'):
            model_name = "test_model"
            model_version = "1.0.0"
            
            save_model(
                model=trained_svm_classifier,
                model_name=model_name,
                model_version=model_version,
                metadata=model_metadata
            )
        
        # Get the metadata
        retrieved_metadata = get_model_metadata(model_name, model_version)
        
        # Check that metadata was retrieved correctly
        assert retrieved_metadata["model_name"] == model_name
        assert retrieved_metadata["model_version"] == model_version
        
        # Check that original metadata was preserved
        for key, value in model_metadata.items():
            assert retrieved_metadata[key] == value
    
    def test_get_model_metadata_latest_version(self, trained_svm_classifier, temp_model_path, model_metadata, monkeypatch):
        """Test getting metadata for the latest model version."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Save multiple model versions
        with patch('models.model_serialization.register_model'):
            model_name = "test_model"
            
            # Save version 1.0.0
            save_model(
                model=trained_svm_classifier,
                model_name=model_name,
                model_version="1.0.0",
                metadata={**model_metadata, "version": "1.0.0"}
            )
            
            # Save version 2.0.0
            save_model(
                model=trained_svm_classifier,
                model_name=model_name,
                model_version="2.0.0",
                metadata={**model_metadata, "version": "2.0.0"}
            )
        
        # Mock _get_latest_model_version to return the latest version
        with patch('models.model_serialization._get_latest_model_version', return_value="2.0.0"):
            # Get metadata without specifying a version
            metadata = get_model_metadata(model_name)
            
            # Check that the latest version's metadata was retrieved
            assert metadata["version"] == "2.0.0"
    
    def test_get_model_metadata_file_not_found(self, temp_model_path, monkeypatch):
        """Test get_model_metadata when the metadata file doesn't exist."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Mock _get_latest_model_version to return a version
        with patch('models.model_serialization._get_latest_model_version', return_value="1.0.0"):
            # Try to get metadata for a non-existent model
            with pytest.raises(FileNotFoundError, match="Metadata file not found"):
                get_model_metadata("non_existent_model", "1.0.0")


# Test register_model function
class TestRegisterModel:
    """Tests for the register_model function."""

    def test_register_model_success(self, temp_model_path, model_metadata, monkeypatch):
        """Test successful model registration."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Mock _load_model_registry and _save_model_registry
        mock_registry = {}
        
        with patch('models.model_serialization._load_model_registry', return_value=mock_registry), \
             patch('models.model_serialization._save_model_registry') as mock_save:
            
            model_name = "test_model"
            model_version = "1.0.0"
            model_path = "/path/to/model.joblib"
            
            # Register the model
            register_model(model_name, model_version, model_path, model_metadata)
            
            # Check that _save_model_registry was called with updated registry
            mock_save.assert_called_once()
            updated_registry = mock_save.call_args[0][0]
            
            # Check that the registry was updated correctly
            assert f"{model_name}_{model_version}" in updated_registry
            entry = updated_registry[f"{model_name}_{model_version}"]
            assert entry["model_name"] == model_name
            assert entry["model_version"] == model_version
            assert entry["model_path"] == model_path
            assert "registered_at" in entry
            assert entry["metadata"] == model_metadata
    
    def test_register_model_update_existing(self, temp_model_path, model_metadata, monkeypatch):
        """Test updating an existing model registration."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Create mock registry with existing entry
        model_name = "test_model"
        model_version = "1.0.0"
        registry_key = f"{model_name}_{model_version}"
        
        mock_registry = {
            registry_key: {
                "model_name": model_name,
                "model_version": model_version,
                "model_path": "/old/path/to/model.joblib",
                "registered_at": "2025-01-01T00:00:00",
                "metadata": {"old": "metadata"}
            }
        }
        
        with patch('models.model_serialization._load_model_registry', return_value=mock_registry), \
             patch('models.model_serialization._save_model_registry') as mock_save:
            
            new_path = "/new/path/to/model.joblib"
            
            # Register the model with updated information
            register_model(model_name, model_version, new_path, model_metadata)
            
            # Check that _save_model_registry was called with updated registry
            mock_save.assert_called_once()
            updated_registry = mock_save.call_args[0][0]
            
            # Check that the registry entry was updated
            assert registry_key in updated_registry
            entry = updated_registry[registry_key]
            assert entry["model_path"] == new_path
            assert entry["metadata"] == model_metadata
            assert entry["registered_at"] != "2025-01-01T00:00:00"  # Should be updated


# Test delete_model function
class TestDeleteModel:
    """Tests for the delete_model function."""

    def test_delete_model_success(self, trained_svm_classifier, temp_model_path, model_metadata, monkeypatch):
        """Test successful model deletion."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Save a model first
        with patch('models.model_serialization.register_model'):
            model_name = "test_model"
            model_version = "1.0.0"
            
            save_model(
                model=trained_svm_classifier,
                model_name=model_name,
                model_version=model_version,
                metadata=model_metadata
            )
        
        # Create mock registry with the model
        registry_key = f"{model_name}_{model_version}"
        mock_registry = {
            registry_key: {
                "model_name": model_name,
                "model_version": model_version,
                "model_path": str(temp_model_path / f"{model_name}_{model_version}.joblib"),
                "metadata": model_metadata
            }
        }
        
        with patch('models.model_serialization._load_model_registry', return_value=mock_registry), \
             patch('models.model_serialization._save_model_registry') as mock_save:
            
            # Delete the model
            result = delete_model(model_name, model_version)
            
            # Check that the function returned success
            assert result is True
            
            # Check that the files were deleted
            assert not (temp_model_path / f"{model_name}_{model_version}.joblib").exists()
            assert not (temp_model_path / f"{model_name}_{model_version}.meta.json").exists()
            assert not (temp_model_path / f"{model_name}_{model_version}.sha256").exists()
            
            # Check that the registry was updated
            mock_save.assert_called_once()
            updated_registry = mock_save.call_args[0][0]
            assert registry_key not in updated_registry
    
    def test_delete_model_invalid_inputs(self):
        """Test delete_model with invalid inputs."""
        # Test with empty model_name
        with pytest.raises(ValueError, match="Model name and version must be provided"):
            delete_model("", "1.0.0")
        
        # Test with empty model_version
        with pytest.raises(ValueError, match="Model name and version must be provided"):
            delete_model("test_model", "")
    
    def test_delete_model_not_found(self, temp_model_path, monkeypatch):
        """Test delete_model when the model doesn't exist."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Mock _load_model_registry to return empty registry
        with patch('models.model_serialization._load_model_registry', return_value={}), \
             patch('models.model_serialization._save_model_registry'):
            
            # Try to delete a non-existent model
            result = delete_model("non_existent_model", "1.0.0")
            
            # Check that the function returned failure
            assert result is False


# Test rollback_model function
class TestRollbackModel:
    """Tests for the rollback_model function."""

    def test_rollback_model_success(self, trained_svm_classifier, temp_model_path, model_metadata, monkeypatch):
        """Test successful model rollback."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Save multiple model versions
        with patch('models.model_serialization.register_model'):
            model_name = "test_model"
            
            # Save version 1.0.0
            save_model(
                model=trained_svm_classifier,
                model_name=model_name,
                model_version="1.0.0",
                metadata=model_metadata
            )
            
            # Save version 2.0.0
            save_model(
                model=trained_svm_classifier,
                model_name=model_name,
                model_version="2.0.0",
                metadata=model_metadata
            )
        
        # Create mock registry with both versions, with 2.0.0 as active
        mock_registry = {
            f"{model_name}_1.0.0": {
                "model_name": model_name,
                "model_version": "1.0.0",
                "is_active": False,
                "model_path": str(temp_model_path / f"{model_name}_1.0.0.joblib"),
                "metadata": model_metadata
            },
            f"{model_name}_2.0.0": {
                "model_name": model_name,
                "model_version": "2.0.0",
                "is_active": True,
                "model_path": str(temp_model_path / f"{model_name}_2.0.0.joblib"),
                "metadata": model_metadata
            }
        }
        
        with patch('models.model_serialization._load_model_registry', return_value=mock_registry), \
             patch('models.model_serialization._save_model_registry') as mock_save:
            
            # Rollback to version 1.0.0
            result = rollback_model(model_name, "1.0.0")
            
            # Check that the function returned success
            assert result is True
            
            # Check that the registry was updated
            mock_save.assert_called_once()
            updated_registry = mock_save.call_args[0][0]
            
            # Check that version 1.0.0 is now active and 2.0.0 is inactive
            assert updated_registry[f"{model_name}_1.0.0"]["is_active"] is True
            assert updated_registry[f"{model_name}_2.0.0"]["is_active"] is False
    
    def test_rollback_model_target_not_found(self, temp_model_path, monkeypatch):
        """Test rollback_model when the target version doesn't exist."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        model_name = "test_model"
        target_version = "1.0.0"
        
        # Mock Path.exists to return False for the target version
        with patch.object(Path, 'exists', return_value=False):
            # Try to rollback to a non-existent version
            result = rollback_model(model_name, target_version)
            
            # Check that the function returned failure
            assert result is False
    
    def test_rollback_model_already_active(self, temp_model_path, monkeypatch):
        """Test rollback_model when the target version is already active."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        model_name = "test_model"
        target_version = "1.0.0"
        
        # Mock Path.exists to return True for the target version
        with patch.object(Path, 'exists', return_value=True), \
             patch('models.model_serialization._get_active_model_version', return_value=target_version):
            
            # Try to rollback to the already active version
            result = rollback_model(model_name, target_version)
            
            # Check that the function returned success
            assert result is True


# Test validate_model function
class TestValidateModel:
    """Tests for the validate_model function."""

    def test_validate_model_success(self, trained_svm_classifier):
        """Test successful model validation."""
        # Validate a valid scikit-learn model
        result = validate_model(trained_svm_classifier)
        assert result is True
    
    def test_validate_model_not_estimator(self):
        """Test validate_model with a non-estimator object."""
        # Test with a dictionary
        with pytest.raises(ValueError, match="Model must be a scikit-learn estimator"):
            validate_model({"not_a_model": True})
        
        # Test with None
        with pytest.raises(ValueError, match="Model must be a scikit-learn estimator"):
            validate_model(None)
    
    def test_validate_model_missing_methods(self):
        """Test validate_model with a model missing required methods."""
        # Create a mock model missing required methods
        class MockModel(BaseEstimator):
            def fit(self, X, y):
                return self
            
            def predict(self, X):
                return [0] * len(X)
            
            # Missing predict_proba method
        
        mock_model = MockModel()
        
        # Validate the model
        with pytest.raises(ValueError, match="Model missing required method: predict_proba"):
            validate_model(mock_model)


# Test helper functions
class TestHelperFunctions:
    """Tests for helper functions in the model_serialization module."""

    def test_calculate_file_hash(self, tmp_path):
        """Test _calculate_file_hash function."""
        # Create a test file with known content
        test_file = tmp_path / "test_file.txt"
        test_content = b"test content for hashing"
        
        with open(test_file, "wb") as f:
            f.write(test_content)
        
        # Calculate hash using the function
        calculated_hash = _calculate_file_hash(test_file)
        
        # Calculate expected hash
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        # Check that the hashes match
        assert calculated_hash == expected_hash
    
    def test_load_model_registry_empty(self, temp_model_path, monkeypatch):
        """Test _load_model_registry when registry file doesn't exist."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Load the registry
        registry = _load_model_registry()
        
        # Check that an empty registry was returned
        assert registry == {}
    
    def test_load_model_registry_existing(self, temp_model_path, monkeypatch):
        """Test _load_model_registry when registry file exists."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Create a test registry file
        registry_path = temp_model_path / "model_registry.json"
        test_registry = {
            "model1_1.0.0": {"model_name": "model1", "model_version": "1.0.0"},
            "model2_1.0.0": {"model_name": "model2", "model_version": "1.0.0"}
        }
        
        with open(registry_path, "w") as f:
            json.dump(test_registry, f)
        
        # Load the registry
        loaded_registry = _load_model_registry()
        
        # Check that the registry was loaded correctly
        assert loaded_registry == test_registry
    
    def test_save_model_registry(self, temp_model_path, monkeypatch):
        """Test _save_model_registry function."""
        # Mock model_config.MODEL_DIRECTORY
        monkeypatch.setattr('models.model_serialization.model_config.MODEL_DIRECTORY', str(temp_model_path))
        
        # Create a test registry
        test_registry = {
            "model1_1.0.0": {"model_name": "model1", "model_version": "1.0.0"},
            "model2_1.0.0": {"model_name": "model2", "model_version": "1.0.0"}
        }
        
        # Save the registry
        _save_model_registry(test_registry)
        
        # Check that the registry file was created
        registry_path = temp_model_path / "model_registry.json"
        assert registry_path.exists()
        
        # Load the saved registry and check its contents
        with open(registry_path, "r") as f:
            saved_registry = json.load(f)
        
        assert saved_registry == test_registry
    
    def test_get_latest_model_version(self):
        """Test _get_latest_model_version function."""
        # Create a mock registry with multiple versions
        mock_registry = {
            "model1_1.0.0": {"model_name": "model1", "model_version": "1.0.0"},
            "model1_1.1.0": {"model_name": "model1", "model_version": "1.1.0"},
            "model1_2.0.0": {"model_name": "model1", "model_version": "2.0.0"},
            "model2_1.0.0": {"model_name": "model2", "model_version": "1.0.0"}
        }
        
        with patch('models.model_serialization._load_model_registry', return_value=mock_registry):
            # Get the latest version for model1
            latest_version = _get_latest_model_version("model1")
            
            # Check that the correct version was returned
            assert latest_version == "2.0.0"
            
            # Get the latest version for model2
            latest_version = _get_latest_model_version("model2")
            assert latest_version == "1.0.0"
            
            # Get the latest version for a non-existent model
            latest_version = _get_latest_model_version("non_existent_model")
            assert latest_version is None
    
    def test_get_active_model_version(self):
        """Test _get_active_model_version function."""
        # Create a mock registry with active and inactive versions
        mock_registry = {
            "model1_1.0.0": {"model_name": "model1", "model_version": "1.0.0", "is_active": False},
            "model1_2.0.0": {"model_name": "model1", "model_version": "2.0.0", "is_active": True},
            "model2_1.0.0": {"model_name": "model2", "model_version": "1.0.0", "is_active": True}
        }
        
        with patch('models.model_serialization._load_model_registry', return_value=mock_registry):
            # Get the active version for model1
            active_version = _get_active_model_version("model1")
            
            # Check that the correct version was returned
            assert active_version == "2.0.0"
            
            # Get the active version for model2
            active_version = _get_active_model_version("model2")
            assert active_version == "1.0.0"
            
            # Get the active version for a non-existent model
            active_version = _get_active_model_version("non_existent_model")
            assert active_version is None
    
    def test_get_active_model_version_fallback(self):
        """Test _get_active_model_version fallback to latest version."""
        # Create a mock registry with no active versions
        mock_registry = {
            "model1_1.0.0": {"model_name": "model1", "model_version": "1.0.0"},
            "model1_2.0.0": {"model_name": "model1", "model_version": "2.0.0"}
        }
        
        with patch('models.model_serialization._load_model_registry', return_value=mock_registry), \
             patch('models.model_serialization._get_latest_model_version', return_value="2.0.0"):
            
            # Get the active version for model1
            active_version = _get_active_model_version("model1")
            
            # Check that it fell back to the latest version
            assert active_version == "2.0.0"