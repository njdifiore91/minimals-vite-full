#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Model serialization utilities for the Document Service.

This module provides functions for saving and loading trained document classification models,
including versioning, metadata storage, and model registry management. It ensures that models
can be persisted and reused across service restarts and deployments.

Functions:
    save_model: Serialize and save a trained model with metadata
    load_model: Load a serialized model with validation
    list_models: List all available models in the registry
    get_model_metadata: Retrieve metadata for a specific model
    register_model: Register a model in the model registry
    delete_model: Remove a model from storage and registry
    rollback_model: Rollback to a previous model version
    validate_model: Validate model integrity and compatibility
"""

import os
import json
import pickle
import hashlib
import logging
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import joblib
import numpy as np
from sklearn.base import BaseEstimator

from ..config import model_config
from ..types.classification import ClassificationModel, ModelMetadata

# Configure logger
logger = logging.getLogger(__name__)

# Constants
MODEL_REGISTRY_FILE = "model_registry.json"
MODEL_EXTENSION = ".joblib"
METADATA_EXTENSION = ".meta.json"
HASH_EXTENSION = ".sha256"


def save_model(
    model: ClassificationModel,
    model_name: str,
    model_version: str,
    metadata: Dict[str, Any],
    model_dir: Optional[str] = None,
) -> str:
    """
    Serialize and save a trained model with metadata.
    
    Args:
        model: The trained scikit-learn model to save
        model_name: Name of the model (e.g., 'svm_classifier', 'random_forest_classifier')
        model_version: Version of the model (e.g., '1.0.0')
        metadata: Dictionary containing model metadata (training parameters, performance metrics, etc.)
        model_dir: Directory to save the model (defaults to config value)
        
    Returns:
        str: Path to the saved model file
        
    Raises:
        ValueError: If model_name or model_version is invalid
        IOError: If the model directory doesn't exist or isn't writable
    """
    # Validate inputs
    if not model_name or not model_version:
        raise ValueError("Model name and version must be provided")
        
    if not isinstance(model, BaseEstimator):
        raise ValueError("Model must be a scikit-learn estimator")
    
    # Use configured model directory if not specified
    if model_dir is None:
        model_dir = model_config.MODEL_DIRECTORY
    
    # Create model directory if it doesn't exist
    model_path = Path(model_dir)
    model_path.mkdir(parents=True, exist_ok=True)
    
    # Generate model filename with version
    model_filename = f"{model_name}_{model_version}{MODEL_EXTENSION}"
    model_filepath = model_path / model_filename
    
    # Generate metadata filename
    metadata_filename = f"{model_name}_{model_version}{METADATA_EXTENSION}"
    metadata_filepath = model_path / metadata_filename
    
    # Generate hash filename
    hash_filename = f"{model_name}_{model_version}{HASH_EXTENSION}"
    hash_filepath = model_path / hash_filename
    
    # Enhance metadata with additional information
    enhanced_metadata = {
        "model_name": model_name,
        "model_version": model_version,
        "created_at": datetime.datetime.now().isoformat(),
        "scikit_learn_version": joblib.__version__,
        "python_version": os.environ.get("PYTHON_VERSION", "unknown"),
        "environment": os.environ.get("ENVIRONMENT", "development"),
        **metadata
    }
    
    try:
        # Serialize the model using joblib (more efficient than pickle for scikit-learn models)
        logger.info(f"Saving model {model_name} version {model_version} to {model_filepath}")
        joblib.dump(model, model_filepath, compress=3)
        
        # Save metadata as JSON
        with open(metadata_filepath, 'w') as f:
            json.dump(enhanced_metadata, f, indent=2)
        
        # Calculate and save model file hash for integrity verification
        model_hash = _calculate_file_hash(model_filepath)
        with open(hash_filepath, 'w') as f:
            f.write(model_hash)
        
        # Register the model in the registry
        register_model(model_name, model_version, str(model_filepath), enhanced_metadata)
        
        logger.info(f"Successfully saved and registered model {model_name} version {model_version}")
        return str(model_filepath)
        
    except Exception as e:
        logger.error(f"Failed to save model {model_name} version {model_version}: {str(e)}")
        # Clean up any partially created files
        for filepath in [model_filepath, metadata_filepath, hash_filepath]:
            if filepath.exists():
                filepath.unlink()
        raise


def load_model(model_name: str, model_version: Optional[str] = None) -> Tuple[ClassificationModel, Dict[str, Any]]:
    """
    Load a serialized model with validation.
    
    Args:
        model_name: Name of the model to load
        model_version: Specific version to load (if None, loads the latest version)
        
    Returns:
        Tuple containing:
            - The loaded model
            - Dictionary of model metadata
        
    Raises:
        FileNotFoundError: If the model file doesn't exist
        ValueError: If the model fails integrity validation
    """
    # Get model directory from config
    model_dir = model_config.MODEL_DIRECTORY
    model_path = Path(model_dir)
    
    # If version not specified, get the latest version
    if model_version is None:
        model_version = _get_latest_model_version(model_name)
        if not model_version:
            raise FileNotFoundError(f"No versions found for model {model_name}")
    
    # Generate filenames
    model_filename = f"{model_name}_{model_version}{MODEL_EXTENSION}"
    model_filepath = model_path / model_filename
    
    metadata_filename = f"{model_name}_{model_version}{METADATA_EXTENSION}"
    metadata_filepath = model_path / metadata_filename
    
    hash_filename = f"{model_name}_{model_version}{HASH_EXTENSION}"
    hash_filepath = model_path / hash_filename
    
    # Check if files exist
    if not model_filepath.exists():
        raise FileNotFoundError(f"Model file not found: {model_filepath}")
    
    if not metadata_filepath.exists():
        logger.warning(f"Metadata file not found: {metadata_filepath}")
        metadata = {"model_name": model_name, "model_version": model_version}
    else:
        # Load metadata
        with open(metadata_filepath, 'r') as f:
            metadata = json.load(f)
    
    # Validate model integrity if hash file exists
    if hash_filepath.exists():
        with open(hash_filepath, 'r') as f:
            stored_hash = f.read().strip()
        
        current_hash = _calculate_file_hash(model_filepath)
        if current_hash != stored_hash:
            raise ValueError(f"Model integrity check failed for {model_name} version {model_version}")
    else:
        logger.warning(f"Hash file not found for integrity check: {hash_filepath}")
    
    try:
        # Load the model using joblib
        logger.info(f"Loading model {model_name} version {model_version} from {model_filepath}")
        model = joblib.load(model_filepath)
        
        # Validate model compatibility
        validate_model(model)
        
        return cast(ClassificationModel, model), metadata
        
    except Exception as e:
        logger.error(f"Failed to load model {model_name} version {model_version}: {str(e)}")
        raise


def list_models() -> List[Dict[str, Any]]:
    """
    List all available models in the registry.
    
    Returns:
        List of dictionaries containing model information
    """
    registry = _load_model_registry()
    return list(registry.values())


def get_model_metadata(model_name: str, model_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve metadata for a specific model.
    
    Args:
        model_name: Name of the model
        model_version: Specific version (if None, gets the latest version)
        
    Returns:
        Dictionary containing model metadata
        
    Raises:
        FileNotFoundError: If the model or metadata doesn't exist
    """
    # Get model directory from config
    model_dir = model_config.MODEL_DIRECTORY
    model_path = Path(model_dir)
    
    # If version not specified, get the latest version
    if model_version is None:
        model_version = _get_latest_model_version(model_name)
        if not model_version:
            raise FileNotFoundError(f"No versions found for model {model_name}")
    
    # Generate metadata filename
    metadata_filename = f"{model_name}_{model_version}{METADATA_EXTENSION}"
    metadata_filepath = model_path / metadata_filename
    
    # Check if metadata file exists
    if not metadata_filepath.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_filepath}")
    
    # Load metadata
    with open(metadata_filepath, 'r') as f:
        metadata = json.load(f)
    
    return metadata


def register_model(model_name: str, model_version: str, model_path: str, metadata: Dict[str, Any]) -> None:
    """
    Register a model in the model registry.
    
    Args:
        model_name: Name of the model
        model_version: Version of the model
        model_path: Path to the model file
        metadata: Dictionary containing model metadata
        
    Raises:
        IOError: If the registry file can't be written
    """
    registry = _load_model_registry()
    
    # Create registry entry
    registry_key = f"{model_name}_{model_version}"
    registry[registry_key] = {
        "model_name": model_name,
        "model_version": model_version,
        "model_path": model_path,
        "registered_at": datetime.datetime.now().isoformat(),
        "metadata": metadata
    }
    
    # Save updated registry
    _save_model_registry(registry)
    logger.info(f"Registered model {model_name} version {model_version} in registry")


def delete_model(model_name: str, model_version: str) -> bool:
    """
    Remove a model from storage and registry.
    
    Args:
        model_name: Name of the model to delete
        model_version: Version of the model to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
        
    Raises:
        ValueError: If model_name or model_version is invalid
    """
    # Validate inputs
    if not model_name or not model_version:
        raise ValueError("Model name and version must be provided")
    
    # Get model directory from config
    model_dir = model_config.MODEL_DIRECTORY
    model_path = Path(model_dir)
    
    # Generate filenames
    model_filename = f"{model_name}_{model_version}{MODEL_EXTENSION}"
    model_filepath = model_path / model_filename
    
    metadata_filename = f"{model_name}_{model_version}{METADATA_EXTENSION}"
    metadata_filepath = model_path / metadata_filename
    
    hash_filename = f"{model_name}_{model_version}{HASH_EXTENSION}"
    hash_filepath = model_path / hash_filename
    
    # Check if model exists
    if not model_filepath.exists():
        logger.warning(f"Model file not found for deletion: {model_filepath}")
        return False
    
    try:
        # Delete model files
        for filepath in [model_filepath, metadata_filepath, hash_filepath]:
            if filepath.exists():
                filepath.unlink()
        
        # Remove from registry
        registry = _load_model_registry()
        registry_key = f"{model_name}_{model_version}"
        if registry_key in registry:
            del registry[registry_key]
            _save_model_registry(registry)
        
        logger.info(f"Successfully deleted model {model_name} version {model_version}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete model {model_name} version {model_version}: {str(e)}")
        return False


def rollback_model(model_name: str, target_version: str) -> bool:
    """
    Rollback to a previous model version.
    
    Args:
        model_name: Name of the model
        target_version: Version to rollback to
        
    Returns:
        bool: True if rollback was successful, False otherwise
    """
    try:
        # Check if target version exists
        model_dir = model_config.MODEL_DIRECTORY
        model_path = Path(model_dir)
        target_model_path = model_path / f"{model_name}_{target_version}{MODEL_EXTENSION}"
        
        if not target_model_path.exists():
            logger.error(f"Target version {target_version} not found for model {model_name}")
            return False
        
        # Get current active version
        current_version = _get_active_model_version(model_name)
        if not current_version:
            logger.warning(f"No active version found for model {model_name}")
        elif current_version == target_version:
            logger.info(f"Model {model_name} is already at version {target_version}")
            return True
        
        # Update active version in registry
        registry = _load_model_registry()
        for key, entry in registry.items():
            if entry["model_name"] == model_name:
                entry["is_active"] = (entry["model_version"] == target_version)
        
        _save_model_registry(registry)
        logger.info(f"Successfully rolled back model {model_name} to version {target_version}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to rollback model {model_name} to version {target_version}: {str(e)}")
        return False


def validate_model(model: Any) -> bool:
    """
    Validate model integrity and compatibility.
    
    Args:
        model: The model to validate
        
    Returns:
        bool: True if model is valid, False otherwise
        
    Raises:
        ValueError: If model fails validation
    """
    # Check if model is a scikit-learn estimator
    if not isinstance(model, BaseEstimator):
        raise ValueError("Model must be a scikit-learn estimator")
    
    # Check for required methods
    required_methods = ["fit", "predict", "predict_proba"]
    for method in required_methods:
        if not hasattr(model, method) or not callable(getattr(model, method)):
            raise ValueError(f"Model missing required method: {method}")
    
    # Additional validation could be added here
    # For example, checking model parameters, feature compatibility, etc.
    
    return True


def _calculate_file_hash(filepath: Union[str, Path]) -> str:
    """
    Calculate SHA-256 hash of a file for integrity verification.
    
    Args:
        filepath: Path to the file
        
    Returns:
        str: Hexadecimal hash string
    """
    filepath = Path(filepath)
    sha256_hash = hashlib.sha256()
    
    with open(filepath, "rb") as f:
        # Read and update hash in chunks to avoid loading large files into memory
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()


def _load_model_registry() -> Dict[str, Dict[str, Any]]:
    """
    Load the model registry from disk.
    
    Returns:
        Dictionary containing model registry entries
    """
    model_dir = model_config.MODEL_DIRECTORY
    registry_path = Path(model_dir) / MODEL_REGISTRY_FILE
    
    if not registry_path.exists():
        return {}
    
    try:
        with open(registry_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load model registry: {str(e)}")
        return {}


def _save_model_registry(registry: Dict[str, Dict[str, Any]]) -> None:
    """
    Save the model registry to disk.
    
    Args:
        registry: Dictionary containing model registry entries
        
    Raises:
        IOError: If the registry file can't be written
    """
    model_dir = model_config.MODEL_DIRECTORY
    model_path = Path(model_dir)
    model_path.mkdir(parents=True, exist_ok=True)
    
    registry_path = model_path / MODEL_REGISTRY_FILE
    
    try:
        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save model registry: {str(e)}")
        raise


def _get_latest_model_version(model_name: str) -> Optional[str]:
    """
    Get the latest version of a model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        str: Latest version number, or None if no versions found
    """
    registry = _load_model_registry()
    versions = []
    
    for key, entry in registry.items():
        if entry["model_name"] == model_name:
            versions.append(entry["model_version"])
    
    if not versions:
        return None
    
    # Sort versions (assuming semantic versioning format)
    versions.sort(key=lambda s: [int(u) for u in s.split('.')], reverse=True)
    return versions[0]


def _get_active_model_version(model_name: str) -> Optional[str]:
    """
    Get the currently active version of a model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        str: Active version number, or None if no active version found
    """
    registry = _load_model_registry()
    
    for key, entry in registry.items():
        if entry["model_name"] == model_name and entry.get("is_active", False):
            return entry["model_version"]
    
    # If no active version is explicitly set, return the latest version
    return _get_latest_model_version(model_name)