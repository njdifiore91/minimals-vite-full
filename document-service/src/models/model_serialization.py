#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Model serialization utilities for the Document Service.

This module provides functions for saving and loading trained document classification models,
with support for versioning, metadata storage, and model registry management. It ensures
models can be persisted and reused across service restarts.

The module implements:
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
import logging
import datetime
import platform
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, BinaryIO, Set

import joblib
import numpy as np
import sklearn

from ..config import model_config
from ..types.classification import ClassificationModel, ModelParameters

# Configure logger
logger = logging.getLogger(__name__)

# Constants
MODEL_REGISTRY_PATH = os.environ.get(
    "MODEL_REGISTRY_PATH", 
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../models")
)
METADATA_EXTENSION = ".metadata.json"
MODEL_EXTENSION = ".model"
CHECKSUM_EXTENSION = ".checksum"
MODEL_REGISTRY_INDEX = "model_registry_index.json"

# Ensure model registry directory exists
Path(MODEL_REGISTRY_PATH).mkdir(parents=True, exist_ok=True)


class ModelSerializationError(Exception):
    """Exception raised for errors during model serialization or deserialization."""
    pass


class ModelVersionError(Exception):
    """Exception raised for errors related to model versioning."""
    pass


class ModelIntegrityError(Exception):
    """Exception raised when model integrity checks fail."""
    pass


class ModelRegistryError(Exception):
    """Exception raised for errors related to the model registry."""
    pass


def calculate_checksum(file_path: str) -> str:
    """
    Calculate SHA-256 checksum of a file for integrity verification.
    
    Args:
        file_path: Path to the file to calculate checksum for
        
    Returns:
        str: Hexadecimal digest of the SHA-256 hash
    """
    sha256_hash = hashlib.sha256()
    
    try:
        with open(file_path, "rb") as f:
            # Read and update hash in chunks to efficiently handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Failed to calculate checksum for {file_path}: {str(e)}")
        raise ModelIntegrityError(f"Checksum calculation failed: {str(e)}")


def verify_checksum(file_path: str, expected_checksum: str) -> bool:
    """
    Verify file integrity by comparing calculated checksum with expected value.
    
    Args:
        file_path: Path to the file to verify
        expected_checksum: Expected SHA-256 checksum
        
    Returns:
        bool: True if checksums match, False otherwise
    """
    try:
        actual_checksum = calculate_checksum(file_path)
        return actual_checksum == expected_checksum
    except Exception as e:
        logger.error(f"Failed to verify checksum for {file_path}: {str(e)}")
        return False


def get_environment_info() -> Dict[str, str]:
    """
    Collect information about the current environment for model metadata.
    
    Returns:
        Dict[str, str]: Dictionary containing environment information
    """
    return {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.platform(),
        "sklearn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "joblib_version": joblib.__version__
    }


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """
    Parse a semantic version string into its components.
    
    Args:
        version_str: Version string in format "major.minor.patch"
        
    Returns:
        Tuple[int, int, int]: Tuple of (major, minor, patch) version numbers
        
    Raises:
        ModelVersionError: If version string is not in the expected format
    """
    try:
        parts = version_str.split('.')
        if len(parts) != 3:
            raise ModelVersionError(f"Invalid version format: {version_str}. Expected 'major.minor.patch'")
        
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError) as e:
        raise ModelVersionError(f"Failed to parse version {version_str}: {str(e)}")


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two semantic version strings.
    
    Args:
        version1: First version string
        version2: Second version string
        
    Returns:
        int: -1 if version1 < version2, 0 if version1 == version2, 1 if version1 > version2
        
    Raises:
        ModelVersionError: If either version string is not in the expected format
    """
    v1 = parse_version(version1)
    v2 = parse_version(version2)
    
    if v1 < v2:
        return -1
    elif v1 > v2:
        return 1
    else:
        return 0


def increment_version(version: str, increment_type: str = "patch") -> str:
    """
    Increment a semantic version string based on the specified increment type.
    
    Args:
        version: Version string to increment
        increment_type: Type of increment ("major", "minor", or "patch")
        
    Returns:
        str: Incremented version string
        
    Raises:
        ModelVersionError: If version string is not in the expected format or
                          increment_type is invalid
    """
    major, minor, patch = parse_version(version)
    
    if increment_type == "major":
        return f"{major + 1}.0.0"
    elif increment_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif increment_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ModelVersionError(f"Invalid increment type: {increment_type}. Expected 'major', 'minor', or 'patch'")


def create_model_metadata(
    model_name: str,
    version: str,
    model_type: str,
    training_parameters: Dict[str, Any],
    performance_metrics: Dict[str, float],
    description: str = "",
    author: str = "",
    tags: List[str] = None
) -> Dict[str, Any]:
    """
    Create metadata for a model.
    
    Args:
        model_name: Name of the model
        version: Version string in format "major.minor.patch"
        model_type: Type of model (e.g., "SVM", "RandomForest")
        training_parameters: Dictionary of parameters used for training
        performance_metrics: Dictionary of performance metrics
        description: Optional description of the model
        author: Optional name of the model author
        tags: Optional list of tags for the model
        
    Returns:
        Dict[str, Any]: Dictionary containing model metadata
    """
    # Validate version format
    parse_version(version)
    
    # Create metadata dictionary
    metadata = {
        "name": model_name,
        "version": version,
        "model_type": model_type,
        "created_at": datetime.datetime.now().isoformat(),
        "training_parameters": training_parameters,
        "performance_metrics": performance_metrics,
        "environment": get_environment_info(),
        "description": description,
        "author": author,
        "tags": tags or []
    }
    
    return metadata


def save_model_metadata(metadata: Dict[str, Any], metadata_path: str) -> None:
    """
    Save model metadata to a JSON file.
    
    Args:
        metadata: Dictionary containing model metadata
        metadata_path: Path to save the metadata file
        
    Raises:
        ModelSerializationError: If metadata cannot be saved
    """
    try:
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved model metadata to {metadata_path}")
    except Exception as e:
        logger.error(f"Failed to save model metadata to {metadata_path}: {str(e)}")
        raise ModelSerializationError(f"Failed to save model metadata: {str(e)}")


def load_model_metadata(metadata_path: str) -> Dict[str, Any]:
    """
    Load model metadata from a JSON file.
    
    Args:
        metadata_path: Path to the metadata file
        
    Returns:
        Dict[str, Any]: Dictionary containing model metadata
        
    Raises:
        ModelSerializationError: If metadata cannot be loaded
    """
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        return metadata
    except Exception as e:
        logger.error(f"Failed to load model metadata from {metadata_path}: {str(e)}")
        raise ModelSerializationError(f"Failed to load model metadata: {str(e)}")


def update_model_registry_index(model_name: str, version: str, model_path: str, metadata_path: str) -> None:
    """
    Update the model registry index with information about a new model version.
    
    Args:
        model_name: Name of the model
        version: Version string
        model_path: Path to the model file
        metadata_path: Path to the metadata file
        
    Raises:
        ModelRegistryError: If registry index cannot be updated
    """
    index_path = os.path.join(MODEL_REGISTRY_PATH, MODEL_REGISTRY_INDEX)
    index = {}
    
    # Load existing index if it exists
    if os.path.exists(index_path):
        try:
            with open(index_path, 'r') as f:
                index = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load existing model registry index: {str(e)}. Creating new index.")
    
    # Initialize model entry if it doesn't exist
    if model_name not in index:
        index[model_name] = {
            "versions": {},
            "latest_version": version
        }
    
    # Add version information
    index[model_name]["versions"][version] = {
        "model_path": model_path,
        "metadata_path": metadata_path,
        "registered_at": datetime.datetime.now().isoformat()
    }
    
    # Update latest version if the new version is greater
    if "latest_version" in index[model_name]:
        latest_version = index[model_name]["latest_version"]
        if compare_versions(version, latest_version) > 0:
            index[model_name]["latest_version"] = version
    else:
        index[model_name]["latest_version"] = version
    
    # Save updated index
    try:
        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2)
        logger.info(f"Updated model registry index with {model_name} version {version}")
    except Exception as e:
        logger.error(f"Failed to update model registry index: {str(e)}")
        raise ModelRegistryError(f"Failed to update model registry index: {str(e)}")


def save_model(
    model: ClassificationModel,
    model_name: str,
    version: str,
    model_type: str,
    training_parameters: Dict[str, Any],
    performance_metrics: Dict[str, float],
    description: str = "",
    author: str = "",
    tags: List[str] = None,
    use_joblib: bool = True
) -> str:
    """
    Save a trained model with metadata and checksum.
    
    Args:
        model: Trained model to save
        model_name: Name of the model
        version: Version string in format "major.minor.patch"
        model_type: Type of model (e.g., "SVM", "RandomForest")
        training_parameters: Dictionary of parameters used for training
        performance_metrics: Dictionary of performance metrics
        description: Optional description of the model
        author: Optional name of the model author
        tags: Optional list of tags for the model
        use_joblib: Whether to use joblib for serialization (recommended for scikit-learn models)
        
    Returns:
        str: Path to the saved model file
        
    Raises:
        ModelSerializationError: If model cannot be saved
    """
    # Create model directory if it doesn't exist
    model_dir = os.path.join(MODEL_REGISTRY_PATH, model_name)
    Path(model_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate file paths
    model_filename = f"{model_name}-{version}{MODEL_EXTENSION}"
    model_path = os.path.join(model_dir, model_filename)
    metadata_path = os.path.join(model_dir, f"{model_name}-{version}{METADATA_EXTENSION}")
    checksum_path = os.path.join(model_dir, f"{model_name}-{version}{CHECKSUM_EXTENSION}")
    
    try:
        # Save model
        if use_joblib:
            joblib.dump(model, model_path, compress=3)
        else:
            with open(model_path, 'wb') as f:
                pickle.dump(model, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        # Calculate and save checksum
        checksum = calculate_checksum(model_path)
        with open(checksum_path, 'w') as f:
            f.write(checksum)
        
        # Create and save metadata
        metadata = create_model_metadata(
            model_name=model_name,
            version=version,
            model_type=model_type,
            training_parameters=training_parameters,
            performance_metrics=performance_metrics,
            description=description,
            author=author,
            tags=tags
        )
        save_model_metadata(metadata, metadata_path)
        
        # Update model registry index
        update_model_registry_index(model_name, version, model_path, metadata_path)
        
        logger.info(f"Successfully saved model {model_name} version {version} to {model_path}")
        return model_path
    
    except Exception as e:
        logger.error(f"Failed to save model {model_name} version {version}: {str(e)}")
        # Clean up any partially created files
        for path in [model_path, metadata_path, checksum_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        raise ModelSerializationError(f"Failed to save model: {str(e)}")


def get_latest_model_version(model_name: str) -> Optional[str]:
    """
    Get the latest version of a model from the registry.
    
    Args:
        model_name: Name of the model
        
    Returns:
        Optional[str]: Latest version string, or None if model not found
    """
    index_path = os.path.join(MODEL_REGISTRY_PATH, MODEL_REGISTRY_INDEX)
    
    if not os.path.exists(index_path):
        return None
    
    try:
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        if model_name in index and "latest_version" in index[model_name]:
            return index[model_name]["latest_version"]
        
        return None
    except Exception as e:
        logger.error(f"Failed to get latest model version: {str(e)}")
        return None


def load_model(model_name: str, version: str = None, verify_integrity: bool = True) -> Tuple[ClassificationModel, Dict[str, Any]]:
    """
    Load a model and its metadata from the model registry.
    
    Args:
        model_name: Name of the model to load
        version: Specific version to load, or None to load the latest version
        verify_integrity: Whether to verify the model file integrity using checksum
        
    Returns:
        Tuple[ClassificationModel, Dict[str, Any]]: Tuple of (model, metadata)
        
    Raises:
        ModelSerializationError: If model cannot be loaded
        ModelIntegrityError: If model integrity check fails
        ModelRegistryError: If model is not found in registry
    """
    # Get model version to load
    if version is None:
        version = get_latest_model_version(model_name)
        if version is None:
            raise ModelRegistryError(f"No versions found for model {model_name}")
    
    # Generate file paths
    model_dir = os.path.join(MODEL_REGISTRY_PATH, model_name)
    model_path = os.path.join(model_dir, f"{model_name}-{version}{MODEL_EXTENSION}")
    metadata_path = os.path.join(model_dir, f"{model_name}-{version}{METADATA_EXTENSION}")
    checksum_path = os.path.join(model_dir, f"{model_name}-{version}{CHECKSUM_EXTENSION}")
    
    # Check if files exist
    if not os.path.exists(model_path):
        raise ModelRegistryError(f"Model file not found: {model_path}")
    if not os.path.exists(metadata_path):
        raise ModelRegistryError(f"Metadata file not found: {metadata_path}")
    
    # Verify integrity if requested
    if verify_integrity and os.path.exists(checksum_path):
        with open(checksum_path, 'r') as f:
            expected_checksum = f.read().strip()
        
        if not verify_checksum(model_path, expected_checksum):
            raise ModelIntegrityError(f"Model integrity check failed for {model_path}")
    
    try:
        # Load model
        try:
            # Try joblib first (faster for scikit-learn models with large arrays)
            model = joblib.load(model_path)
        except Exception as joblib_error:
            logger.warning(f"Failed to load model with joblib: {str(joblib_error)}. Trying pickle.")
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
        
        # Load metadata
        metadata = load_model_metadata(metadata_path)
        
        logger.info(f"Successfully loaded model {model_name} version {version} from {model_path}")
        return model, metadata
    
    except Exception as e:
        logger.error(f"Failed to load model {model_name} version {version}: {str(e)}")
        raise ModelSerializationError(f"Failed to load model: {str(e)}")


def list_models() -> List[str]:
    """
    List all models in the registry.
    
    Returns:
        List[str]: List of model names
    """
    index_path = os.path.join(MODEL_REGISTRY_PATH, MODEL_REGISTRY_INDEX)
    
    if not os.path.exists(index_path):
        return []
    
    try:
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        return list(index.keys())
    except Exception as e:
        logger.error(f"Failed to list models: {str(e)}")
        return []


def list_model_versions(model_name: str) -> List[str]:
    """
    List all versions of a model in the registry.
    
    Args:
        model_name: Name of the model
        
    Returns:
        List[str]: List of version strings, sorted from newest to oldest
        
    Raises:
        ModelRegistryError: If model is not found in registry
    """
    index_path = os.path.join(MODEL_REGISTRY_PATH, MODEL_REGISTRY_INDEX)
    
    if not os.path.exists(index_path):
        raise ModelRegistryError(f"Model registry index not found: {index_path}")
    
    try:
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        if model_name not in index:
            raise ModelRegistryError(f"Model {model_name} not found in registry")
        
        versions = list(index[model_name]["versions"].keys())
        # Sort versions in descending order (newest first)
        versions.sort(key=lambda v: parse_version(v), reverse=True)
        
        return versions
    except Exception as e:
        if isinstance(e, ModelRegistryError):
            raise
        logger.error(f"Failed to list model versions: {str(e)}")
        raise ModelRegistryError(f"Failed to list model versions: {str(e)}")


def get_model_info(model_name: str, version: str = None) -> Dict[str, Any]:
    """
    Get detailed information about a model version.
    
    Args:
        model_name: Name of the model
        version: Specific version to get info for, or None to get the latest version
        
    Returns:
        Dict[str, Any]: Dictionary containing model information
        
    Raises:
        ModelRegistryError: If model or version is not found in registry
    """
    # Get model version to load
    if version is None:
        version = get_latest_model_version(model_name)
        if version is None:
            raise ModelRegistryError(f"No versions found for model {model_name}")
    
    # Get metadata path
    model_dir = os.path.join(MODEL_REGISTRY_PATH, model_name)
    metadata_path = os.path.join(model_dir, f"{model_name}-{version}{METADATA_EXTENSION}")
    
    # Check if metadata file exists
    if not os.path.exists(metadata_path):
        raise ModelRegistryError(f"Metadata file not found: {metadata_path}")
    
    try:
        # Load metadata
        metadata = load_model_metadata(metadata_path)
        
        # Get registry information
        index_path = os.path.join(MODEL_REGISTRY_PATH, MODEL_REGISTRY_INDEX)
        if os.path.exists(index_path):
            with open(index_path, 'r') as f:
                index = json.load(f)
            
            if model_name in index and "versions" in index[model_name] and version in index[model_name]["versions"]:
                registry_info = index[model_name]["versions"][version]
                metadata["registry_info"] = registry_info
        
        return metadata
    except Exception as e:
        logger.error(f"Failed to get model info for {model_name} version {version}: {str(e)}")
        raise ModelRegistryError(f"Failed to get model info: {str(e)}")


def delete_model_version(model_name: str, version: str) -> bool:
    """
    Delete a specific version of a model from the registry.
    
    Args:
        model_name: Name of the model
        version: Version to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
        
    Raises:
        ModelRegistryError: If model or version is not found in registry or cannot be deleted
    """
    index_path = os.path.join(MODEL_REGISTRY_PATH, MODEL_REGISTRY_INDEX)
    
    if not os.path.exists(index_path):
        raise ModelRegistryError(f"Model registry index not found: {index_path}")
    
    try:
        # Load registry index
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        # Check if model and version exist
        if model_name not in index:
            raise ModelRegistryError(f"Model {model_name} not found in registry")
        if "versions" not in index[model_name] or version not in index[model_name]["versions"]:
            raise ModelRegistryError(f"Version {version} of model {model_name} not found in registry")
        
        # Get file paths
        model_dir = os.path.join(MODEL_REGISTRY_PATH, model_name)
        model_path = os.path.join(model_dir, f"{model_name}-{version}{MODEL_EXTENSION}")
        metadata_path = os.path.join(model_dir, f"{model_name}-{version}{METADATA_EXTENSION}")
        checksum_path = os.path.join(model_dir, f"{model_name}-{version}{CHECKSUM_EXTENSION}")
        
        # Delete files
        files_to_delete = [model_path, metadata_path, checksum_path]
        for file_path in files_to_delete:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Update registry index
        del index[model_name]["versions"][version]
        
        # If this was the latest version, update latest_version
        if "latest_version" in index[model_name] and index[model_name]["latest_version"] == version:
            if index[model_name]["versions"]:  # If there are other versions
                # Find the highest remaining version
                remaining_versions = list(index[model_name]["versions"].keys())
                remaining_versions.sort(key=lambda v: parse_version(v), reverse=True)
                index[model_name]["latest_version"] = remaining_versions[0]
            else:  # No versions left
                index[model_name]["latest_version"] = None
        
        # If no versions left, remove the model entry
        if not index[model_name]["versions"]:
            del index[model_name]
        
        # Save updated index
        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2)
        
        logger.info(f"Successfully deleted model {model_name} version {version}")
        return True
    
    except Exception as e:
        if isinstance(e, ModelRegistryError):
            raise
        logger.error(f"Failed to delete model {model_name} version {version}: {str(e)}")
        raise ModelRegistryError(f"Failed to delete model version: {str(e)}")


def compare_model_versions(model_name: str, version1: str, version2: str) -> Dict[str, Any]:
    """
    Compare two versions of a model.
    
    Args:
        model_name: Name of the model
        version1: First version to compare
        version2: Second version to compare
        
    Returns:
        Dict[str, Any]: Dictionary containing comparison results
        
    Raises:
        ModelRegistryError: If model or versions are not found in registry
    """
    try:
        # Get metadata for both versions
        metadata1 = get_model_info(model_name, version1)
        metadata2 = get_model_info(model_name, version2)
        
        # Compare performance metrics
        performance_diff = {}
        for metric, value in metadata1.get("performance_metrics", {}).items():
            if metric in metadata2.get("performance_metrics", {}):
                performance_diff[metric] = {
                    "version1": value,
                    "version2": metadata2["performance_metrics"][metric],
                    "difference": metadata2["performance_metrics"][metric] - value
                }
        
        # Compare training parameters
        param_diff = {}
        for param, value in metadata1.get("training_parameters", {}).items():
            if param in metadata2.get("training_parameters", {}):
                if value != metadata2["training_parameters"][param]:
                    param_diff[param] = {
                        "version1": value,
                        "version2": metadata2["training_parameters"][param]
                    }
            else:
                param_diff[param] = {
                    "version1": value,
                    "version2": None
                }
        
        for param, value in metadata2.get("training_parameters", {}).items():
            if param not in metadata1.get("training_parameters", {}):
                param_diff[param] = {
                    "version1": None,
                    "version2": value
                }
        
        # Create comparison result
        comparison = {
            "model_name": model_name,
            "version1": version1,
            "version2": version2,
            "created_at1": metadata1.get("created_at"),
            "created_at2": metadata2.get("created_at"),
            "performance_diff": performance_diff,
            "parameter_diff": param_diff,
            "environment_diff": {
                key: {
                    "version1": metadata1.get("environment", {}).get(key),
                    "version2": metadata2.get("environment", {}).get(key)
                }
                for key in set(metadata1.get("environment", {}).keys()) | set(metadata2.get("environment", {}).keys())
                if metadata1.get("environment", {}).get(key) != metadata2.get("environment", {}).get(key)
            }
        }
        
        return comparison
    
    except Exception as e:
        if isinstance(e, ModelRegistryError):
            raise
        logger.error(f"Failed to compare model versions: {str(e)}")
        raise ModelRegistryError(f"Failed to compare model versions: {str(e)}")


def find_models_by_tag(tag: str) -> List[Dict[str, Any]]:
    """
    Find models that have a specific tag.
    
    Args:
        tag: Tag to search for
        
    Returns:
        List[Dict[str, Any]]: List of model information dictionaries
    """
    results = []
    
    try:
        # Get all models
        models = list_models()
        
        for model_name in models:
            # Get all versions of the model
            try:
                versions = list_model_versions(model_name)
                
                for version in versions:
                    # Get model info
                    try:
                        info = get_model_info(model_name, version)
                        
                        # Check if tag is in the tags list
                        if tag in info.get("tags", []):
                            results.append({
                                "model_name": model_name,
                                "version": version,
                                "info": info
                            })
                    except Exception:
                        # Skip this version if we can't get info
                        continue
            except Exception:
                # Skip this model if we can't get versions
                continue
        
        return results
    
    except Exception as e:
        logger.error(f"Failed to find models by tag {tag}: {str(e)}")
        return []


def export_model(model_name: str, version: str, export_dir: str) -> str:
    """
    Export a model and its metadata to a specified directory.
    
    Args:
        model_name: Name of the model
        version: Version to export
        export_dir: Directory to export to
        
    Returns:
        str: Path to the exported model directory
        
    Raises:
        ModelRegistryError: If model or version is not found in registry or cannot be exported
    """
    try:
        # Create export directory if it doesn't exist
        export_path = os.path.join(export_dir, f"{model_name}-{version}")
        Path(export_path).mkdir(parents=True, exist_ok=True)
        
        # Get file paths
        model_dir = os.path.join(MODEL_REGISTRY_PATH, model_name)
        model_path = os.path.join(model_dir, f"{model_name}-{version}{MODEL_EXTENSION}")
        metadata_path = os.path.join(model_dir, f"{model_name}-{version}{METADATA_EXTENSION}")
        checksum_path = os.path.join(model_dir, f"{model_name}-{version}{CHECKSUM_EXTENSION}")
        
        # Check if files exist
        if not os.path.exists(model_path):
            raise ModelRegistryError(f"Model file not found: {model_path}")
        if not os.path.exists(metadata_path):
            raise ModelRegistryError(f"Metadata file not found: {metadata_path}")
        
        # Copy files to export directory
        import shutil
        shutil.copy2(model_path, os.path.join(export_path, f"{model_name}-{version}{MODEL_EXTENSION}"))
        shutil.copy2(metadata_path, os.path.join(export_path, f"{model_name}-{version}{METADATA_EXTENSION}"))
        if os.path.exists(checksum_path):
            shutil.copy2(checksum_path, os.path.join(export_path, f"{model_name}-{version}{CHECKSUM_EXTENSION}"))
        
        logger.info(f"Successfully exported model {model_name} version {version} to {export_path}")
        return export_path
    
    except Exception as e:
        if isinstance(e, ModelRegistryError):
            raise
        logger.error(f"Failed to export model {model_name} version {version}: {str(e)}")
        raise ModelRegistryError(f"Failed to export model: {str(e)}")


def import_model(import_dir: str, model_name: str = None, version: str = None) -> Tuple[str, str]:
    """
    Import a model and its metadata from a specified directory.
    
    Args:
        import_dir: Directory to import from
        model_name: Optional new name for the model (if None, use original name)
        version: Optional new version for the model (if None, use original version)
        
    Returns:
        Tuple[str, str]: Tuple of (model_name, version) of the imported model
        
    Raises:
        ModelRegistryError: If model cannot be imported
    """
    try:
        # Find model and metadata files in import directory
        import_files = os.listdir(import_dir)
        model_files = [f for f in import_files if f.endswith(MODEL_EXTENSION)]
        metadata_files = [f for f in import_files if f.endswith(METADATA_EXTENSION)]
        
        if not model_files:
            raise ModelRegistryError(f"No model files found in {import_dir}")
        if not metadata_files:
            raise ModelRegistryError(f"No metadata files found in {import_dir}")
        
        # Use the first model and metadata file found
        model_file = model_files[0]
        metadata_file = metadata_files[0]
        
        # Load metadata to get original model name and version
        metadata_path = os.path.join(import_dir, metadata_file)
        metadata = load_model_metadata(metadata_path)
        
        # Determine model name and version to use
        orig_model_name = metadata.get("name")
        orig_version = metadata.get("version")
        
        if not model_name:
            model_name = orig_model_name
        if not version:
            version = orig_version
        
        if not model_name or not version:
            raise ModelRegistryError("Could not determine model name or version")
        
        # Create model directory if it doesn't exist
        model_dir = os.path.join(MODEL_REGISTRY_PATH, model_name)
        Path(model_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate file paths
        new_model_path = os.path.join(model_dir, f"{model_name}-{version}{MODEL_EXTENSION}")
        new_metadata_path = os.path.join(model_dir, f"{model_name}-{version}{METADATA_EXTENSION}")
        
        # Check if model already exists
        if os.path.exists(new_model_path):
            raise ModelRegistryError(f"Model {model_name} version {version} already exists in registry")
        
        # Copy files to model registry
        import shutil
        shutil.copy2(os.path.join(import_dir, model_file), new_model_path)
        
        # Update metadata if model name or version changed
        if model_name != orig_model_name or version != orig_version:
            metadata["name"] = model_name
            metadata["version"] = version
            save_model_metadata(metadata, new_metadata_path)
        else:
            shutil.copy2(metadata_path, new_metadata_path)
        
        # Calculate and save checksum
        checksum = calculate_checksum(new_model_path)
        checksum_path = os.path.join(model_dir, f"{model_name}-{version}{CHECKSUM_EXTENSION}")
        with open(checksum_path, 'w') as f:
            f.write(checksum)
        
        # Update model registry index
        update_model_registry_index(model_name, version, new_model_path, new_metadata_path)
        
        logger.info(f"Successfully imported model {model_name} version {version} from {import_dir}")
        return model_name, version
    
    except Exception as e:
        if isinstance(e, ModelRegistryError):
            raise
        logger.error(f"Failed to import model from {import_dir}: {str(e)}")
        raise ModelRegistryError(f"Failed to import model: {str(e)}")


def rollback_model(model_name: str, target_version: str) -> bool:
    """
    Rollback to a previous version of a model by setting it as the latest version.
    
    Args:
        model_name: Name of the model
        target_version: Version to rollback to
        
    Returns:
        bool: True if rollback was successful, False otherwise
        
    Raises:
        ModelRegistryError: If model or version is not found in registry or cannot be rolled back
    """
    index_path = os.path.join(MODEL_REGISTRY_PATH, MODEL_REGISTRY_INDEX)
    
    if not os.path.exists(index_path):
        raise ModelRegistryError(f"Model registry index not found: {index_path}")
    
    try:
        # Load registry index
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        # Check if model and version exist
        if model_name not in index:
            raise ModelRegistryError(f"Model {model_name} not found in registry")
        if "versions" not in index[model_name] or target_version not in index[model_name]["versions"]:
            raise ModelRegistryError(f"Version {target_version} of model {model_name} not found in registry")
        
        # Update latest version
        index[model_name]["latest_version"] = target_version
        
        # Save updated index
        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2)
        
        logger.info(f"Successfully rolled back model {model_name} to version {target_version}")
        return True
    
    except Exception as e:
        if isinstance(e, ModelRegistryError):
            raise
        logger.error(f"Failed to rollback model {model_name} to version {target_version}: {str(e)}")
        raise ModelRegistryError(f"Failed to rollback model: {str(e)}")