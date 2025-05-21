#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for model serialization utilities.

This module contains tests for the model_serialization.py module, which provides
functions for saving and loading trained document classification models, with
support for versioning, metadata storage, and model registry management.

The tests verify that the serialization module correctly handles:
- Model serialization using pickle and joblib
- Model versioning system with metadata
- Model registry for tracking deployed models
- Secure model storage with integrity checks
- Model metadata storage for tracking training parameters
"""

import os
import json
import pickle
import hashlib
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC

from src.models import model_serialization
from src.models.model_serialization import (
    calculate_checksum,
    verify_checksum,
    get_environment_info,
    parse_version,
    compare_versions,
    increment_version,
    create_model_metadata,
    save_model_metadata,
    load_model_metadata,
    update_model_registry_index,
    save_model,
    get_latest_model_version,
    load_model,
    list_models,
    list_model_versions,
    get_model_info,
    delete_model_version,
    compare_model_versions,
    find_models_by_tag,
    export_model,
    import_model,
    rollback_model,
    ModelSerializationError,
    ModelVersionError,
    ModelIntegrityError,
    ModelRegistryError
)


# Test fixtures
@pytest.fixture
def test_model_registry_path(tmp_path):
    """Create a temporary directory for model registry testing."""
    registry_path = tmp_path / "model_registry"
    registry_path.mkdir()
    
    # Patch the MODEL_REGISTRY_PATH constant
    original_path = model_serialization.MODEL_REGISTRY_PATH
    model_serialization.MODEL_REGISTRY_PATH = str(registry_path)
    
    yield str(registry_path)
    
    # Restore the original path
    model_serialization.MODEL_REGISTRY_PATH = original_path


@pytest.fixture
def sample_model():
    """Create a simple SVM model for testing."""
    return SVC(probability=True, random_state=42)


@pytest.fixture
def sample_model_metadata():
    """Create sample model metadata for testing."""
    return {
        "name": "test_model",
        "version": "1.0.0",
        "model_type": "svm",
        "created_at": datetime.now().isoformat(),
        "training_parameters": {
            "C": 1.0,
            "kernel": "rbf",
            "gamma": "scale",
            "probability": True,
            "random_state": 42
        },
        "performance_metrics": {
            "accuracy": 0.95,
            "precision": 0.94,
            "recall": 0.93,
            "f1": 0.935
        },
        "environment": get_environment_info(),
        "description": "Test model for unit testing",
        "author": "Test Author",
        "tags": ["test", "svm", "classification"]
    }


# Tests for checksum calculation and verification
class TestChecksumFunctions:
    
    def test_calculate_checksum(self, tmp_path):
        """Test that calculate_checksum correctly computes SHA-256 hash."""
        # Create a test file with known content
        test_file = tmp_path / "test_file.txt"
        test_content = b"Test content for checksum calculation"
        test_file.write_bytes(test_content)
        
        # Calculate checksum
        checksum = calculate_checksum(str(test_file))
        
        # Calculate expected checksum
        expected_checksum = hashlib.sha256(test_content).hexdigest()
        
        assert checksum == expected_checksum
    
    def test_verify_checksum_valid(self, tmp_path):
        """Test that verify_checksum returns True for valid checksums."""
        # Create a test file with known content
        test_file = tmp_path / "test_file.txt"
        test_content = b"Test content for checksum verification"
        test_file.write_bytes(test_content)
        
        # Calculate expected checksum
        expected_checksum = hashlib.sha256(test_content).hexdigest()
        
        # Verify checksum
        result = verify_checksum(str(test_file), expected_checksum)
        
        assert result is True
    
    def test_verify_checksum_invalid(self, tmp_path):
        """Test that verify_checksum returns False for invalid checksums."""
        # Create a test file with known content
        test_file = tmp_path / "test_file.txt"
        test_content = b"Test content for checksum verification"
        test_file.write_bytes(test_content)
        
        # Use an invalid checksum
        invalid_checksum = "invalid_checksum_value"
        
        # Verify checksum
        result = verify_checksum(str(test_file), invalid_checksum)
        
        assert result is False
    
    def test_calculate_checksum_file_not_found(self):
        """Test that calculate_checksum raises ModelIntegrityError for non-existent files."""
        with pytest.raises(ModelIntegrityError):
            calculate_checksum("/path/to/nonexistent/file")


# Tests for version management functions
class TestVersionManagement:
    
    def test_parse_version_valid(self):
        """Test that parse_version correctly parses valid version strings."""
        version = "1.2.3"
        result = parse_version(version)
        assert result == (1, 2, 3)
    
    def test_parse_version_invalid_format(self):
        """Test that parse_version raises ModelVersionError for invalid format."""
        with pytest.raises(ModelVersionError):
            parse_version("1.2")
        
        with pytest.raises(ModelVersionError):
            parse_version("1.2.3.4")
        
        with pytest.raises(ModelVersionError):
            parse_version("invalid")
    
    def test_parse_version_invalid_numbers(self):
        """Test that parse_version raises ModelVersionError for non-numeric components."""
        with pytest.raises(ModelVersionError):
            parse_version("1.a.3")
    
    def test_compare_versions(self):
        """Test that compare_versions correctly compares version strings."""
        # Equal versions
        assert compare_versions("1.0.0", "1.0.0") == 0
        
        # First version greater
        assert compare_versions("2.0.0", "1.0.0") == 1
        assert compare_versions("1.1.0", "1.0.0") == 1
        assert compare_versions("1.0.1", "1.0.0") == 1
        
        # First version less
        assert compare_versions("1.0.0", "2.0.0") == -1
        assert compare_versions("1.0.0", "1.1.0") == -1
        assert compare_versions("1.0.0", "1.0.1") == -1
    
    def test_increment_version(self):
        """Test that increment_version correctly increments version components."""
        # Major increment
        assert increment_version("1.0.0", "major") == "2.0.0"
        
        # Minor increment
        assert increment_version("1.0.0", "minor") == "1.1.0"
        
        # Patch increment
        assert increment_version("1.0.0", "patch") == "1.0.1"
    
    def test_increment_version_invalid_type(self):
        """Test that increment_version raises ModelVersionError for invalid increment type."""
        with pytest.raises(ModelVersionError):
            increment_version("1.0.0", "invalid")


# Tests for model metadata functions
class TestModelMetadata:
    
    def test_create_model_metadata(self):
        """Test that create_model_metadata creates valid metadata."""
        # Create metadata
        metadata = create_model_metadata(
            model_name="test_model",
            version="1.0.0",
            model_type="svm",
            training_parameters={"C": 1.0, "kernel": "rbf"},
            performance_metrics={"accuracy": 0.95},
            description="Test model",
            author="Test Author",
            tags=["test", "svm"]
        )
        
        # Check required fields
        assert metadata["name"] == "test_model"
        assert metadata["version"] == "1.0.0"
        assert metadata["model_type"] == "svm"
        assert "created_at" in metadata
        assert metadata["training_parameters"] == {"C": 1.0, "kernel": "rbf"}
        assert metadata["performance_metrics"] == {"accuracy": 0.95}
        assert "environment" in metadata
        assert metadata["description"] == "Test model"
        assert metadata["author"] == "Test Author"
        assert metadata["tags"] == ["test", "svm"]
    
    def test_create_model_metadata_invalid_version(self):
        """Test that create_model_metadata raises ModelVersionError for invalid version."""
        with pytest.raises(ModelVersionError):
            create_model_metadata(
                model_name="test_model",
                version="invalid",
                model_type="svm",
                training_parameters={},
                performance_metrics={}
            )
    
    def test_save_load_model_metadata(self, tmp_path):
        """Test that save_model_metadata and load_model_metadata work correctly."""
        # Create metadata
        metadata = create_model_metadata(
            model_name="test_model",
            version="1.0.0",
            model_type="svm",
            training_parameters={"C": 1.0, "kernel": "rbf"},
            performance_metrics={"accuracy": 0.95}
        )
        
        # Save metadata
        metadata_path = tmp_path / "metadata.json"
        save_model_metadata(metadata, str(metadata_path))
        
        # Check that file exists
        assert metadata_path.exists()
        
        # Load metadata
        loaded_metadata = load_model_metadata(str(metadata_path))
        
        # Check that loaded metadata matches original
        assert loaded_metadata == metadata
    
    def test_save_model_metadata_error(self, tmp_path):
        """Test that save_model_metadata raises ModelSerializationError on failure."""
        # Create metadata
        metadata = create_model_metadata(
            model_name="test_model",
            version="1.0.0",
            model_type="svm",
            training_parameters={},
            performance_metrics={}
        )
        
        # Use a directory path instead of a file path
        invalid_path = tmp_path
        
        with pytest.raises(ModelSerializationError):
            save_model_metadata(metadata, str(invalid_path))
    
    def test_load_model_metadata_error(self):
        """Test that load_model_metadata raises ModelSerializationError on failure."""
        with pytest.raises(ModelSerializationError):
            load_model_metadata("/path/to/nonexistent/metadata.json")


# Tests for model registry functions
class TestModelRegistry:
    
    def test_update_model_registry_index(self, test_model_registry_path):
        """Test that update_model_registry_index correctly updates the registry index."""
        # Define test data
        model_name = "test_model"
        version = "1.0.0"
        model_path = os.path.join(test_model_registry_path, "test_model.pkl")
        metadata_path = os.path.join(test_model_registry_path, "test_model_metadata.json")
        
        # Update registry index
        update_model_registry_index(model_name, version, model_path, metadata_path)
        
        # Check that index file exists
        index_path = os.path.join(test_model_registry_path, "model_registry_index.json")
        assert os.path.exists(index_path)
        
        # Load index and check contents
        with open(index_path, "r") as f:
            index = json.load(f)
        
        assert model_name in index
        assert "versions" in index[model_name]
        assert version in index[model_name]["versions"]
        assert index[model_name]["versions"][version]["model_path"] == model_path
        assert index[model_name]["versions"][version]["metadata_path"] == metadata_path
        assert "registered_at" in index[model_name]["versions"][version]
        assert index[model_name]["latest_version"] == version
    
    def test_update_model_registry_index_multiple_versions(self, test_model_registry_path):
        """Test that update_model_registry_index correctly handles multiple versions."""
        # Define test data
        model_name = "test_model"
        version1 = "1.0.0"
        version2 = "1.1.0"
        model_path1 = os.path.join(test_model_registry_path, "test_model_1.0.0.pkl")
        model_path2 = os.path.join(test_model_registry_path, "test_model_1.1.0.pkl")
        metadata_path1 = os.path.join(test_model_registry_path, "test_model_1.0.0_metadata.json")
        metadata_path2 = os.path.join(test_model_registry_path, "test_model_1.1.0_metadata.json")
        
        # Update registry index with first version
        update_model_registry_index(model_name, version1, model_path1, metadata_path1)
        
        # Update registry index with second version
        update_model_registry_index(model_name, version2, model_path2, metadata_path2)
        
        # Load index and check contents
        index_path = os.path.join(test_model_registry_path, "model_registry_index.json")
        with open(index_path, "r") as f:
            index = json.load(f)
        
        assert model_name in index
        assert "versions" in index[model_name]
        assert version1 in index[model_name]["versions"]
        assert version2 in index[model_name]["versions"]
        assert index[model_name]["latest_version"] == version2  # Latest version should be updated
    
    def test_get_latest_model_version(self, test_model_registry_path):
        """Test that get_latest_model_version returns the correct version."""
        # Define test data
        model_name = "test_model"
        version1 = "1.0.0"
        version2 = "1.1.0"
        model_path1 = os.path.join(test_model_registry_path, "test_model_1.0.0.pkl")
        model_path2 = os.path.join(test_model_registry_path, "test_model_1.1.0.pkl")
        metadata_path1 = os.path.join(test_model_registry_path, "test_model_1.0.0_metadata.json")
        metadata_path2 = os.path.join(test_model_registry_path, "test_model_1.1.0_metadata.json")
        
        # Update registry index with both versions
        update_model_registry_index(model_name, version1, model_path1, metadata_path1)
        update_model_registry_index(model_name, version2, model_path2, metadata_path2)
        
        # Get latest version
        latest_version = get_latest_model_version(model_name)
        
        assert latest_version == version2
    
    def test_get_latest_model_version_nonexistent_model(self, test_model_registry_path):
        """Test that get_latest_model_version returns None for nonexistent models."""
        latest_version = get_latest_model_version("nonexistent_model")
        assert latest_version is None
    
    def test_list_models(self, test_model_registry_path):
        """Test that list_models returns all models in the registry."""
        # Define test data
        model1_name = "test_model_1"
        model2_name = "test_model_2"
        version = "1.0.0"
        model1_path = os.path.join(test_model_registry_path, "test_model_1.pkl")
        model2_path = os.path.join(test_model_registry_path, "test_model_2.pkl")
        metadata1_path = os.path.join(test_model_registry_path, "test_model_1_metadata.json")
        metadata2_path = os.path.join(test_model_registry_path, "test_model_2_metadata.json")
        
        # Update registry index with both models
        update_model_registry_index(model1_name, version, model1_path, metadata1_path)
        update_model_registry_index(model2_name, version, model2_path, metadata2_path)
        
        # List models
        models = list_models()
        
        assert model1_name in models
        assert model2_name in models
    
    def test_list_model_versions(self, test_model_registry_path):
        """Test that list_model_versions returns all versions of a model."""
        # Define test data
        model_name = "test_model"
        version1 = "1.0.0"
        version2 = "1.1.0"
        version3 = "2.0.0"
        model_path1 = os.path.join(test_model_registry_path, "test_model_1.0.0.pkl")
        model_path2 = os.path.join(test_model_registry_path, "test_model_1.1.0.pkl")
        model_path3 = os.path.join(test_model_registry_path, "test_model_2.0.0.pkl")
        metadata_path1 = os.path.join(test_model_registry_path, "test_model_1.0.0_metadata.json")
        metadata_path2 = os.path.join(test_model_registry_path, "test_model_1.1.0_metadata.json")
        metadata_path3 = os.path.join(test_model_registry_path, "test_model_2.0.0_metadata.json")
        
        # Update registry index with all versions
        update_model_registry_index(model_name, version1, model_path1, metadata_path1)
        update_model_registry_index(model_name, version2, model_path2, metadata_path2)
        update_model_registry_index(model_name, version3, model_path3, metadata_path3)
        
        # List model versions
        versions = list_model_versions(model_name)
        
        # Versions should be sorted in descending order (newest first)
        assert versions == [version3, version2, version1]
    
    def test_list_model_versions_nonexistent_model(self, test_model_registry_path):
        """Test that list_model_versions raises ModelRegistryError for nonexistent models."""
        with pytest.raises(ModelRegistryError):
            list_model_versions("nonexistent_model")


# Tests for model serialization and deserialization
class TestModelSerialization:
    
    def test_save_model_joblib(self, test_model_registry_path, trained_svm_classifier):
        """Test that save_model correctly saves a model using joblib."""
        # Define test data
        model_name = "svm_classifier"
        version = "1.0.0"
        model_type = "svm"
        training_parameters = {"C": 1.0, "kernel": "rbf"}
        performance_metrics = {"accuracy": 0.95}
        
        # Save model
        model_path = save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version,
            model_type=model_type,
            training_parameters=training_parameters,
            performance_metrics=performance_metrics,
            use_joblib=True
        )
        
        # Check that model file exists
        assert os.path.exists(model_path)
        
        # Check that metadata file exists
        metadata_path = os.path.join(
            test_model_registry_path,
            model_name,
            f"{model_name}-{version}.metadata.json"
        )
        assert os.path.exists(metadata_path)
        
        # Check that checksum file exists
        checksum_path = os.path.join(
            test_model_registry_path,
            model_name,
            f"{model_name}-{version}.checksum"
        )
        assert os.path.exists(checksum_path)
        
        # Check that model registry index is updated
        index_path = os.path.join(test_model_registry_path, "model_registry_index.json")
        with open(index_path, "r") as f:
            index = json.load(f)
        
        assert model_name in index
        assert version in index[model_name]["versions"]
    
    def test_save_model_pickle(self, test_model_registry_path, trained_svm_classifier):
        """Test that save_model correctly saves a model using pickle."""
        # Define test data
        model_name = "svm_classifier_pickle"
        version = "1.0.0"
        model_type = "svm"
        training_parameters = {"C": 1.0, "kernel": "rbf"}
        performance_metrics = {"accuracy": 0.95}
        
        # Save model
        model_path = save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version,
            model_type=model_type,
            training_parameters=training_parameters,
            performance_metrics=performance_metrics,
            use_joblib=False
        )
        
        # Check that model file exists
        assert os.path.exists(model_path)
    
    def test_load_model_joblib(self, test_model_registry_path, trained_svm_classifier):
        """Test that load_model correctly loads a model saved with joblib."""
        # Define test data
        model_name = "svm_classifier_load"
        version = "1.0.0"
        model_type = "svm"
        training_parameters = {"C": 1.0, "kernel": "rbf"}
        performance_metrics = {"accuracy": 0.95}
        
        # Save model
        save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version,
            model_type=model_type,
            training_parameters=training_parameters,
            performance_metrics=performance_metrics,
            use_joblib=True
        )
        
        # Load model
        loaded_model, metadata = load_model(model_name, version)
        
        # Check that loaded model is the correct type
        assert isinstance(loaded_model, SVC)
        
        # Check that metadata is correct
        assert metadata["name"] == model_name
        assert metadata["version"] == version
        assert metadata["model_type"] == model_type
        assert metadata["training_parameters"] == training_parameters
        assert metadata["performance_metrics"] == performance_metrics
    
    def test_load_model_latest_version(self, test_model_registry_path, trained_svm_classifier):
        """Test that load_model correctly loads the latest version when version is None."""
        # Define test data
        model_name = "svm_classifier_versions"
        version1 = "1.0.0"
        version2 = "1.1.0"
        model_type = "svm"
        training_parameters = {"C": 1.0, "kernel": "rbf"}
        performance_metrics = {"accuracy": 0.95}
        
        # Save model version 1.0.0
        save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version1,
            model_type=model_type,
            training_parameters=training_parameters,
            performance_metrics=performance_metrics
        )
        
        # Save model version 1.1.0
        save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version2,
            model_type=model_type,
            training_parameters=training_parameters,
            performance_metrics=performance_metrics
        )
        
        # Load latest model version
        loaded_model, metadata = load_model(model_name)
        
        # Check that loaded model is from version 1.1.0
        assert metadata["version"] == version2
    
    def test_load_model_integrity_check(self, test_model_registry_path, trained_svm_classifier):
        """Test that load_model performs integrity check when requested."""
        # Define test data
        model_name = "svm_classifier_integrity"
        version = "1.0.0"
        model_type = "svm"
        training_parameters = {"C": 1.0, "kernel": "rbf"}
        performance_metrics = {"accuracy": 0.95}
        
        # Save model
        model_path = save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version,
            model_type=model_type,
            training_parameters=training_parameters,
            performance_metrics=performance_metrics
        )
        
        # Corrupt the model file
        with open(model_path, "wb") as f:
            f.write(b"corrupted data")
        
        # Load model with integrity check
        with pytest.raises(ModelIntegrityError):
            load_model(model_name, version, verify_integrity=True)
    
    def test_load_model_nonexistent(self, test_model_registry_path):
        """Test that load_model raises ModelRegistryError for nonexistent models."""
        with pytest.raises(ModelRegistryError):
            load_model("nonexistent_model")
    
    def test_load_model_nonexistent_version(self, test_model_registry_path, trained_svm_classifier):
        """Test that load_model raises ModelRegistryError for nonexistent versions."""
        # Define test data
        model_name = "svm_classifier_version_error"
        version = "1.0.0"
        model_type = "svm"
        training_parameters = {"C": 1.0, "kernel": "rbf"}
        performance_metrics = {"accuracy": 0.95}
        
        # Save model
        save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version,
            model_type=model_type,
            training_parameters=training_parameters,
            performance_metrics=performance_metrics
        )
        
        # Try to load nonexistent version
        with pytest.raises(ModelRegistryError):
            load_model(model_name, "2.0.0")


# Tests for model registry management
class TestModelRegistryManagement:
    
    def test_get_model_info(self, test_model_registry_path, trained_svm_classifier):
        """Test that get_model_info returns correct model information."""
        # Define test data
        model_name = "svm_classifier_info"
        version = "1.0.0"
        model_type = "svm"
        training_parameters = {"C": 1.0, "kernel": "rbf"}
        performance_metrics = {"accuracy": 0.95}
        
        # Save model
        save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version,
            model_type=model_type,
            training_parameters=training_parameters,
            performance_metrics=performance_metrics
        )
        
        # Get model info
        info = get_model_info(model_name, version)
        
        # Check that info contains expected fields
        assert info["name"] == model_name
        assert info["version"] == version
        assert info["model_type"] == model_type
        assert info["training_parameters"] == training_parameters
        assert info["performance_metrics"] == performance_metrics
        assert "registry_info" in info
    
    def test_delete_model_version(self, test_model_registry_path, trained_svm_classifier):
        """Test that delete_model_version correctly removes a model version."""
        # Define test data
        model_name = "svm_classifier_delete"
        version = "1.0.0"
        model_type = "svm"
        training_parameters = {"C": 1.0, "kernel": "rbf"}
        performance_metrics = {"accuracy": 0.95}
        
        # Save model
        model_path = save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version,
            model_type=model_type,
            training_parameters=training_parameters,
            performance_metrics=performance_metrics
        )
        
        # Delete model version
        result = delete_model_version(model_name, version)
        
        # Check that deletion was successful
        assert result is True
        
        # Check that model file is deleted
        assert not os.path.exists(model_path)
        
        # Check that model is removed from registry
        with pytest.raises(ModelRegistryError):
            get_model_info(model_name, version)
    
    def test_delete_model_version_multiple_versions(self, test_model_registry_path, trained_svm_classifier):
        """Test that delete_model_version correctly handles multiple versions."""
        # Define test data
        model_name = "svm_classifier_delete_multi"
        version1 = "1.0.0"
        version2 = "1.1.0"
        model_type = "svm"
        training_parameters = {"C": 1.0, "kernel": "rbf"}
        performance_metrics = {"accuracy": 0.95}
        
        # Save model version 1.0.0
        save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version1,
            model_type=model_type,
            training_parameters=training_parameters,
            performance_metrics=performance_metrics
        )
        
        # Save model version 1.1.0
        save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version2,
            model_type=model_type,
            training_parameters=training_parameters,
            performance_metrics=performance_metrics
        )
        
        # Delete version 1.1.0
        delete_model_version(model_name, version2)
        
        # Check that latest version is updated to 1.0.0
        latest_version = get_latest_model_version(model_name)
        assert latest_version == version1
    
    def test_compare_model_versions(self, test_model_registry_path, trained_svm_classifier):
        """Test that compare_model_versions correctly compares two model versions."""
        # Define test data
        model_name = "svm_classifier_compare"
        version1 = "1.0.0"
        version2 = "1.1.0"
        model_type = "svm"
        training_parameters1 = {"C": 1.0, "kernel": "rbf"}
        training_parameters2 = {"C": 2.0, "kernel": "linear"}
        performance_metrics1 = {"accuracy": 0.95}
        performance_metrics2 = {"accuracy": 0.97}
        
        # Save model version 1.0.0
        save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version1,
            model_type=model_type,
            training_parameters=training_parameters1,
            performance_metrics=performance_metrics1
        )
        
        # Save model version 1.1.0
        save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version2,
            model_type=model_type,
            training_parameters=training_parameters2,
            performance_metrics=performance_metrics2
        )
        
        # Compare model versions
        comparison = compare_model_versions(model_name, version1, version2)
        
        # Check that comparison contains expected fields
        assert comparison["model_name"] == model_name
        assert comparison["version1"] == version1
        assert comparison["version2"] == version2
        assert "performance_diff" in comparison
        assert "parameter_diff" in comparison
        assert "environment_diff" in comparison
        
        # Check performance difference
        assert "accuracy" in comparison["performance_diff"]
        assert comparison["performance_diff"]["accuracy"]["version1"] == 0.95
        assert comparison["performance_diff"]["accuracy"]["version2"] == 0.97
        assert comparison["performance_diff"]["accuracy"]["difference"] == 0.02
        
        # Check parameter difference
        assert "C" in comparison["parameter_diff"]
        assert comparison["parameter_diff"]["C"]["version1"] == 1.0
        assert comparison["parameter_diff"]["C"]["version2"] == 2.0
        assert "kernel" in comparison["parameter_diff"]
        assert comparison["parameter_diff"]["kernel"]["version1"] == "rbf"
        assert comparison["parameter_diff"]["kernel"]["version2"] == "linear"
    
    def test_find_models_by_tag(self, test_model_registry_path, trained_svm_classifier, trained_random_forest_classifier):
        """Test that find_models_by_tag correctly finds models with a specific tag."""
        # Define test data
        svm_model_name = "svm_classifier_tag"
        rf_model_name = "rf_classifier_tag"
        version = "1.0.0"
        svm_tags = ["svm", "classification", "test"]
        rf_tags = ["random_forest", "classification", "test"]
        
        # Save SVM model
        save_model(
            model=trained_svm_classifier,
            model_name=svm_model_name,
            version=version,
            model_type="svm",
            training_parameters={"C": 1.0, "kernel": "rbf"},
            performance_metrics={"accuracy": 0.95},
            tags=svm_tags
        )
        
        # Save Random Forest model
        save_model(
            model=trained_random_forest_classifier,
            model_name=rf_model_name,
            version=version,
            model_type="random_forest",
            training_parameters={"n_estimators": 100},
            performance_metrics={"accuracy": 0.96},
            tags=rf_tags
        )
        
        # Find models with "classification" tag
        results = find_models_by_tag("classification")
        
        # Check that both models are found
        assert len(results) == 2
        model_names = [result["model_name"] for result in results]
        assert svm_model_name in model_names
        assert rf_model_name in model_names
        
        # Find models with "svm" tag
        results = find_models_by_tag("svm")
        
        # Check that only SVM model is found
        assert len(results) == 1
        assert results[0]["model_name"] == svm_model_name
    
    def test_export_import_model(self, test_model_registry_path, trained_svm_classifier, tmp_path):
        """Test that export_model and import_model correctly export and import models."""
        # Define test data
        model_name = "svm_classifier_export"
        version = "1.0.0"
        model_type = "svm"
        training_parameters = {"C": 1.0, "kernel": "rbf"}
        performance_metrics = {"accuracy": 0.95}
        export_dir = str(tmp_path / "export")
        os.makedirs(export_dir, exist_ok=True)
        
        # Save model
        save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version,
            model_type=model_type,
            training_parameters=training_parameters,
            performance_metrics=performance_metrics
        )
        
        # Export model
        export_path = export_model(model_name, version, export_dir)
        
        # Check that export directory exists
        assert os.path.exists(export_path)
        
        # Check that exported files exist
        assert os.path.exists(os.path.join(export_path, f"{model_name}-{version}.model"))
        assert os.path.exists(os.path.join(export_path, f"{model_name}-{version}.metadata.json"))
        assert os.path.exists(os.path.join(export_path, f"{model_name}-{version}.checksum"))
        
        # Delete original model
        delete_model_version(model_name, version)
        
        # Import model with new name
        new_model_name = "svm_classifier_import"
        imported_name, imported_version = import_model(export_path, new_model_name)
        
        # Check that import was successful
        assert imported_name == new_model_name
        assert imported_version == version
        
        # Check that imported model exists in registry
        info = get_model_info(new_model_name, version)
        assert info["name"] == new_model_name
        assert info["version"] == version
        assert info["model_type"] == model_type
        assert info["training_parameters"] == training_parameters
        assert info["performance_metrics"] == performance_metrics
    
    def test_rollback_model(self, test_model_registry_path, trained_svm_classifier):
        """Test that rollback_model correctly sets an older version as the latest version."""
        # Define test data
        model_name = "svm_classifier_rollback"
        version1 = "1.0.0"
        version2 = "1.1.0"
        model_type = "svm"
        training_parameters = {"C": 1.0, "kernel": "rbf"}
        performance_metrics = {"accuracy": 0.95}
        
        # Save model version 1.0.0
        save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version1,
            model_type=model_type,
            training_parameters=training_parameters,
            performance_metrics=performance_metrics
        )
        
        # Save model version 1.1.0
        save_model(
            model=trained_svm_classifier,
            model_name=model_name,
            version=version2,
            model_type=model_type,
            training_parameters=training_parameters,
            performance_metrics=performance_metrics
        )
        
        # Check that latest version is 1.1.0
        latest_version = get_latest_model_version(model_name)
        assert latest_version == version2
        
        # Rollback to version 1.0.0
        result = rollback_model(model_name, version1)
        
        # Check that rollback was successful
        assert result is True
        
        # Check that latest version is now 1.0.0
        latest_version = get_latest_model_version(model_name)
        assert latest_version == version1