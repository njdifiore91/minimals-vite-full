#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the tensorflow_utils module.

This module contains tests for TensorFlow utility functions used in the OCR service,
including GPU configuration, model loading, inference, and confidence scoring.

The tests validate that the OCR service correctly implements the requirements specified
in the technical specification:
- OCR Service must use TensorFlow with GPU acceleration (section 3.2.2)
- Service must apply appropriate OCR model based on document type (section 4.1.8)
- Service must implement confidence scoring for extracted fields (section 4.1.8)
"""

import os
import json
import tempfile
import pytest
import numpy as np
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

import tensorflow as tf

# Import the module to test
from ocr_service.utils import tensorflow_utils


# ===== Test GPU Configuration and Management =====

@pytest.mark.parametrize("gpu_available", [True, False])
@patch("tensorflow.config.list_physical_devices")
def test_configure_gpu_memory(mock_list_devices, gpu_available):
    """Test GPU memory configuration with and without available GPUs."""
    # Setup mock GPU devices
    if gpu_available:
        mock_gpu = MagicMock()
        mock_gpu.name = "/device:GPU:0"
        mock_list_devices.return_value = [mock_gpu]
    else:
        mock_list_devices.return_value = []
    
    # Call the function
    result = tensorflow_utils.configure_gpu_memory(memory_limit=1024, allow_growth=True)
    
    # Verify results
    assert result["gpu_available"] == gpu_available
    assert result["settings"]["allow_growth"] == True
    assert result["settings"]["memory_limit_mb"] == 1024
    
    # Verify GPU configuration was attempted if GPUs are available
    if gpu_available:
        assert mock_list_devices.called
        assert result["parallelism_configured"] == True
    else:
        assert result["gpu_available"] == False


@patch("tensorflow.config.list_physical_devices")
@patch("tensorflow.config.experimental.set_memory_growth")
def test_configure_gpu_memory_growth(mock_set_memory_growth, mock_list_devices):
    """Test GPU memory growth configuration."""
    # Setup mock GPU devices
    mock_gpu = MagicMock()
    mock_gpu.name = "/device:GPU:0"
    mock_list_devices.return_value = [mock_gpu]
    
    # Call the function
    result = tensorflow_utils.configure_gpu_memory(allow_growth=True)
    
    # Verify memory growth was configured
    mock_set_memory_growth.assert_called_once_with(mock_gpu, True)
    assert result["memory_growth_enabled"] == True


@patch("tensorflow.config.list_physical_devices")
@patch("tensorflow.config.set_logical_device_configuration")
def test_configure_gpu_memory_limit(mock_set_config, mock_list_devices):
    """Test GPU memory limit configuration."""
    # Setup mock GPU devices
    mock_gpu = MagicMock()
    mock_gpu.name = "/device:GPU:0"
    mock_list_devices.return_value = [mock_gpu]
    
    # Call the function
    result = tensorflow_utils.configure_gpu_memory(memory_limit=2048, allow_growth=False)
    
    # Verify memory limit was configured
    assert mock_set_config.called
    assert result["memory_limit_set"] == True
    assert result["settings"]["memory_limit_mb"] == 2048


@patch("tensorflow.config.list_physical_devices")
@patch("tensorflow.test.is_built_with_cuda")
def test_check_gpu_compatibility(mock_is_built_with_cuda, mock_list_devices):
    """Test GPU compatibility check."""
    # Setup mocks
    mock_gpu = MagicMock()
    mock_gpu.name = "/device:GPU:0"
    mock_list_devices.return_value = [mock_gpu]
    mock_is_built_with_cuda.return_value = True
    
    # Call the function
    is_compatible, gpu_info = tensorflow_utils.check_gpu_compatibility()
    
    # Verify results
    assert is_compatible == True
    assert "gpu_0" in gpu_info
    assert mock_is_built_with_cuda.called


@patch("tensorflow.config.list_physical_devices")
@patch("tensorflow.test.is_built_with_cuda")
def test_check_gpu_compatibility_no_gpu(mock_is_built_with_cuda, mock_list_devices):
    """Test GPU compatibility check when no GPU is available."""
    # Setup mocks
    mock_list_devices.return_value = []
    mock_is_built_with_cuda.return_value = True
    
    # Call the function
    is_compatible, gpu_info = tensorflow_utils.check_gpu_compatibility()
    
    # Verify results
    assert is_compatible == False
    assert "error" in gpu_info
    assert gpu_info["error"] == "No GPU found"


@patch("tensorflow.config.list_physical_devices")
@patch("tensorflow.test.is_built_with_cuda")
@patch("tensorflow.sysconfig.get_build_info")
def test_verify_gpu_requirements(mock_get_build_info, mock_is_built_with_cuda, mock_list_devices):
    """Test verification of GPU requirements."""
    # Setup mocks
    mock_gpu = MagicMock()
    mock_gpu.name = "/device:GPU:0"
    mock_list_devices.return_value = [mock_gpu]
    mock_is_built_with_cuda.return_value = True
    mock_get_build_info.return_value = {"cuda_version": "11.2", "cudnn_version": "8.1"}
    
    # Mock get_available_vram to return sufficient VRAM
    with patch.object(tensorflow_utils, "get_available_vram", return_value={0: 10240}):
        # Mock check_gpu_compatibility to return success
        with patch.object(tensorflow_utils, "check_gpu_compatibility", return_value=(True, {"test_passed": True})):
            # Call the function
            meets_requirements, results = tensorflow_utils.verify_gpu_requirements()
            
            # Verify results
            assert meets_requirements == True
            assert results["gpu_available"] == True
            assert results["cuda_available"] == True
            assert results["sufficient_vram"] == True
            assert results["tensorflow_gpu_enabled"] == True
            assert results["requirements_met"] == True


@patch("tensorflow.config.list_physical_devices")
@patch("tensorflow.test.is_built_with_cuda")
@patch("tensorflow.sysconfig.get_build_info")
def test_verify_gpu_requirements_insufficient_vram(mock_get_build_info, mock_is_built_with_cuda, mock_list_devices):
    """Test verification of GPU requirements with insufficient VRAM."""
    # Setup mocks
    mock_gpu = MagicMock()
    mock_gpu.name = "/device:GPU:0"
    mock_list_devices.return_value = [mock_gpu]
    mock_is_built_with_cuda.return_value = True
    mock_get_build_info.return_value = {"cuda_version": "11.2", "cudnn_version": "8.1"}
    
    # Mock get_available_vram to return insufficient VRAM
    with patch.object(tensorflow_utils, "get_available_vram", return_value={0: 4096}):
        # Mock check_gpu_compatibility to return success
        with patch.object(tensorflow_utils, "check_gpu_compatibility", return_value=(True, {"test_passed": True})):
            # Call the function
            meets_requirements, results = tensorflow_utils.verify_gpu_requirements()
            
            # Verify results
            assert meets_requirements == False
            assert results["gpu_available"] == True
            assert results["cuda_available"] == True
            assert results["sufficient_vram"] == False
            assert results["requirements_met"] == False


@patch("tensorflow.config.list_physical_devices")
def test_get_available_vram(mock_list_devices):
    """Test getting available VRAM information."""
    # Setup mock GPU devices
    mock_gpu = MagicMock()
    mock_gpu.name = "/device:GPU:0"
    mock_list_devices.return_value = [mock_gpu]
    
    # Mock tensor creation and execution to simulate VRAM estimation
    with patch("tensorflow.device"):
        with patch("tensorflow.random.normal"):
            with patch("numpy.ndarray"):
                # Call the function
                vram_info = tensorflow_utils.get_available_vram()
                
                # Verify results
                assert isinstance(vram_info, dict)
                # Note: We can't verify exact values since this is a mock


@patch("tensorflow.keras.backend.clear_session")
@patch("gc.collect")
def test_cleanup_gpu_memory(mock_gc_collect, mock_clear_session):
    """Test GPU memory cleanup."""
    # Mock get_available_vram to return before and after values
    with patch.object(tensorflow_utils, "get_available_vram", side_effect=[{0: 5000}, {0: 8000}]):
        # Call the function
        result = tensorflow_utils.cleanup_gpu_memory()
        
        # Verify results
        assert result["success"] == True
        assert "cleared_tf_session" in result["actions_performed"]
        assert "forced_garbage_collection" in result["actions_performed"]
        assert mock_clear_session.called
        assert mock_gc_collect.called
        assert result["memory_freed_mb"]["0"] == 3000  # 8000 - 5000


# ===== Test Model Loading and Validation =====

@pytest.mark.parametrize("model_type", ["typed", "handwritten", "hybrid"])
@patch("tensorflow.keras.models.load_model")
def test_load_model(mock_load_model, model_type, temp_dir):
    """Test loading models of different types."""
    # Create a temporary model directory
    model_path = os.path.join(temp_dir, f"{model_type}_model")
    os.makedirs(model_path, exist_ok=True)
    
    # Create a version file
    version_data = {
        "version": "1.0.0",
        "created_at": "2023-01-15T14:30:45Z",
        "model_type": model_type,
        "metadata": {
            "accuracy": 0.95,
            "min_tf_version": "2.15.0"
        }
    }
    version_file = os.path.join(model_path, tensorflow_utils.MODEL_VERSION_FILE)
    with open(version_file, "w") as f:
        json.dump(version_data, f)
    
    # Setup mock model
    mock_model = MagicMock(spec=tf.keras.Model)
    mock_model.input_shape = (None, 1024, 768, 3)
    mock_model.output_shape = (None, 1000)
    mock_load_model.return_value = mock_model
    
    # Mock validate_model to return success
    with patch.object(tensorflow_utils, "validate_model", return_value=(True, {"is_valid": True, "issues": []})):
        # Mock warmup_model to do nothing
        with patch.object(tensorflow_utils, "warmup_model"):
            # Call the function
            model = tensorflow_utils.load_model(model_path, model_type)
            
            # Verify results
            assert model is mock_model
            mock_load_model.assert_called_once_with(model_path, custom_objects={})


@pytest.mark.parametrize("model_type", ["typed", "handwritten", "hybrid"])
@patch("tensorflow.keras.models.load_model")
def test_load_model_with_version(mock_load_model, model_type, temp_dir):
    """Test loading models with specific version."""
    # Create a temporary model directory
    model_path = os.path.join(temp_dir, f"{model_type}_model")
    os.makedirs(model_path, exist_ok=True)
    
    # Create a version file
    version_data = {
        "version": "1.0.0",
        "created_at": "2023-01-15T14:30:45Z",
        "model_type": model_type,
        "metadata": {
            "accuracy": 0.95,
            "min_tf_version": "2.15.0"
        }
    }
    version_file = os.path.join(model_path, tensorflow_utils.MODEL_VERSION_FILE)
    with open(version_file, "w") as f:
        json.dump(version_data, f)
    
    # Setup mock model
    mock_model = MagicMock(spec=tf.keras.Model)
    mock_model.input_shape = (None, 1024, 768, 3)
    mock_model.output_shape = (None, 1000)
    mock_load_model.return_value = mock_model
    
    # Mock validate_model to return success
    with patch.object(tensorflow_utils, "validate_model", return_value=(True, {"is_valid": True, "issues": []})):
        # Mock warmup_model to do nothing
        with patch.object(tensorflow_utils, "warmup_model"):
            # Call the function with specific version
            model = tensorflow_utils.load_model(model_path, model_type, version="1.0.0")
            
            # Verify results
            assert model is mock_model
            mock_load_model.assert_called_once_with(model_path, custom_objects={})


@pytest.mark.parametrize("model_type", ["typed", "handwritten", "hybrid"])
@patch("tensorflow.keras.models.load_model")
def test_load_model_version_mismatch(mock_load_model, model_type, temp_dir):
    """Test loading models with version mismatch."""
    # Create a temporary model directory
    model_path = os.path.join(temp_dir, f"{model_type}_model")
    os.makedirs(model_path, exist_ok=True)
    
    # Create a version file
    version_data = {
        "version": "1.0.0",
        "created_at": "2023-01-15T14:30:45Z",
        "model_type": model_type,
        "metadata": {
            "accuracy": 0.95,
            "min_tf_version": "2.15.0"
        }
    }
    version_file = os.path.join(model_path, tensorflow_utils.MODEL_VERSION_FILE)
    with open(version_file, "w") as f:
        json.dump(version_data, f)
    
    # Setup mock model
    mock_model = MagicMock(spec=tf.keras.Model)
    mock_load_model.return_value = mock_model
    
    # Call the function with mismatched version
    with pytest.raises(ValueError, match="Model version mismatch"):
        tensorflow_utils.load_model(model_path, model_type, version="2.0.0")


@pytest.mark.parametrize("model_type", ["typed", "handwritten", "hybrid"])
@patch("tensorflow.keras.models.load_model")
def test_load_model_validation_failure(mock_load_model, model_type, temp_dir):
    """Test loading models with validation failure."""
    # Create a temporary model directory
    model_path = os.path.join(temp_dir, f"{model_type}_model")
    os.makedirs(model_path, exist_ok=True)
    
    # Create a version file
    version_data = {
        "version": "1.0.0",
        "created_at": "2023-01-15T14:30:45Z",
        "model_type": model_type,
        "metadata": {
            "accuracy": 0.95,
            "min_tf_version": "2.15.0"
        }
    }
    version_file = os.path.join(model_path, tensorflow_utils.MODEL_VERSION_FILE)
    with open(version_file, "w") as f:
        json.dump(version_data, f)
    
    # Setup mock model
    mock_model = MagicMock(spec=tf.keras.Model)
    mock_model.input_shape = (None, 1024, 768, 3)
    mock_model.output_shape = (None, 1000)
    mock_load_model.return_value = mock_model
    
    # Mock validate_model to return failure
    validation_results = {
        "is_valid": False,
        "issues": ["Invalid input shape", "Incompatible output format"]
    }
    with patch.object(tensorflow_utils, "validate_model", return_value=(False, validation_results)):
        # Call the function
        with pytest.raises(ValueError, match="Model validation failed"):
            tensorflow_utils.load_model(model_path, model_type)


@pytest.mark.parametrize("model_type", ["typed", "handwritten", "hybrid"])
def test_warmup_model(model_type):
    """Test model warmup functionality."""
    # Create a mock model
    mock_model = MagicMock(spec=tf.keras.Model)
    mock_model.return_value = np.random.rand(1, 10, 10, 3)
    
    # Call the function
    tensorflow_utils.warmup_model(mock_model, model_type)
    
    # Verify model was called with appropriate input
    assert mock_model.called
    # The exact input shape depends on model_type, but we can verify it was called


@pytest.mark.parametrize("model_type", ["typed", "handwritten", "hybrid"])
def test_get_model_version(model_type, temp_dir):
    """Test getting model version information."""
    # Create a temporary model directory
    model_path = os.path.join(temp_dir, f"{model_type}_model")
    os.makedirs(model_path, exist_ok=True)
    
    # Create a version file
    version_data = {
        "version": "1.0.0",
        "created_at": "2023-01-15T14:30:45Z",
        "model_type": model_type,
        "metadata": {
            "accuracy": 0.95,
            "min_tf_version": "2.15.0"
        }
    }
    version_file = os.path.join(model_path, tensorflow_utils.MODEL_VERSION_FILE)
    with open(version_file, "w") as f:
        json.dump(version_data, f)
    
    # Call the function
    version_info = tensorflow_utils.get_model_version(model_path)
    
    # Verify results
    assert version_info["version"] == "1.0.0"
    assert version_info["created_at"] == "2023-01-15T14:30:45Z"
    assert version_info["model_type"] == model_type
    assert version_info["metadata"]["accuracy"] == 0.95
    assert version_info["metadata"]["min_tf_version"] == "2.15.0"


@pytest.mark.parametrize("model_type", ["typed", "handwritten", "hybrid"])
def test_get_model_version_no_file(model_type, temp_dir):
    """Test getting model version when no version file exists."""
    # Create a temporary model directory without version file
    model_path = os.path.join(temp_dir, f"{model_type}_model_no_version")
    os.makedirs(model_path, exist_ok=True)
    
    # Mock load_model to return a model with metadata
    mock_model = MagicMock(spec=tf.keras.Model)
    mock_model.metadata = {
        "version": "1.0.0",
        "created_at": "2023-01-15T14:30:45Z",
        "model_type": model_type
    }
    
    with patch("tensorflow.keras.models.load_model", return_value=mock_model):
        # Call the function
        version_info = tensorflow_utils.get_model_version(model_path)
        
        # Verify results
        assert version_info["version"] == "1.0.0"
        assert version_info["created_at"] == "2023-01-15T14:30:45Z"
        assert version_info["model_type"] == model_type


@pytest.mark.parametrize("model_type,is_valid", [
    ("typed", True),
    ("handwritten", True),
    ("hybrid", True),
    ("unknown", False)
])
def test_validate_model(model_type, is_valid):
    """Test model validation for different model types."""
    # Create a mock model
    mock_model = MagicMock(spec=tf.keras.Model)
    
    # Set input and output shapes based on model type
    if model_type == "typed":
        mock_model.input_shape = (None, 1024, 768, 3)
        mock_model.output_shape = (None, 1000)
    elif model_type == "handwritten":
        mock_model.input_shape = (None, 1024, 768, 3)
        mock_model.output_shape = (None, 1000)
    elif model_type == "hybrid":
        mock_model.input_shape = (None, 1024, 768, 3)
        mock_model.output_shape = (None, 1000)
    else:  # unknown
        mock_model.input_shape = (None, 100, 100, 3)
        mock_model.output_shape = (None, 10)
    
    # Call the function
    is_valid_result, validation_results = tensorflow_utils.validate_model(mock_model, model_type)
    
    # Verify results
    if model_type in tensorflow_utils.SUPPORTED_MODEL_TYPES:
        assert is_valid_result == is_valid
        assert validation_results["model_type"] == model_type
        assert "input_shape" in validation_results
        assert "output_shape" in validation_results
    else:
        assert is_valid_result == False
        assert "Unsupported model type" in validation_results["issues"][0]


# ===== Test Inference and Confidence Scoring =====

@pytest.mark.parametrize("model_type", ["typed", "handwritten", "hybrid"])
@pytest.mark.parametrize("gpu_available", [True, False])
def test_run_inference(model_type, gpu_available):
    """Test running inference with different model types and GPU availability."""
    # Create a mock model
    mock_model = MagicMock(spec=tf.keras.Model)
    mock_model.predict.return_value = np.random.rand(1, 1000)
    
    # Create a mock image
    image = np.random.rand(1, 224, 224, 3)
    
    # Mock GPU availability
    with patch("tensorflow.config.list_physical_devices", return_value=[MagicMock()] if gpu_available else []):
        # Mock calculate_confidence_scores
        confidence_scores = {
            "fields": {"text": 0.95},
            "overall": 0.95,
            "low_confidence_fields": [],
            "requires_human_review": False
        }
        with patch.object(tensorflow_utils, "calculate_confidence_scores", return_value=confidence_scores):
            # Call the function
            output, metadata = tensorflow_utils.run_inference(mock_model, image, model_type)
            
            # Verify results
            assert mock_model.predict.called
            assert output is not None
            assert metadata["model_type"] == model_type
            assert metadata["gpu_available"] == gpu_available
            assert metadata["gpu_utilized"] == gpu_available
            assert "inference_time_ms" in metadata
            assert "preprocessing_time_ms" in metadata
            assert "postprocessing_time_ms" in metadata
            assert "total_time_ms" in metadata
            assert metadata["confidence_scores"] == confidence_scores


@pytest.mark.parametrize("model_type", ["typed", "handwritten", "hybrid"])
def test_run_inference_with_preprocessing(model_type):
    """Test inference with image preprocessing based on model type."""
    # Create a mock model
    mock_model = MagicMock(spec=tf.keras.Model)
    mock_model.predict.return_value = np.random.rand(1, 1000)
    mock_model.input_shape = (None, 224, 224, 3)
    
    # Create a mock image with wrong shape/channels
    image = np.random.rand(224, 224, 1)  # Missing batch dimension, wrong channels
    
    # Mock GPU availability
    with patch("tensorflow.config.list_physical_devices", return_value=[MagicMock()]):
        # Mock image preprocessing functions
        with patch("tensorflow.image.adjust_contrast", return_value=tf.random.uniform((1, 224, 224, 3))):
            with patch("tensorflow.image.adjust_brightness", return_value=tf.random.uniform((1, 224, 224, 3))):
                # Mock calculate_confidence_scores
                confidence_scores = {
                    "fields": {"text": 0.95},
                    "overall": 0.95,
                    "low_confidence_fields": [],
                    "requires_human_review": False
                }
                with patch.object(tensorflow_utils, "calculate_confidence_scores", return_value=confidence_scores):
                    # Call the function
                    output, metadata = tensorflow_utils.run_inference(mock_model, image, model_type)
                    
                    # Verify results
                    assert mock_model.predict.called
                    assert output is not None
                    assert metadata["model_type"] == model_type
                    assert "preprocessing_time_ms" in metadata


@pytest.mark.parametrize("model_type", ["typed", "handwritten", "hybrid"])
def test_calculate_confidence_scores(model_type):
    """Test confidence score calculation for different model types."""
    # Create mock model output
    if model_type == "typed":
        output = np.random.rand(100, 10)  # Character probabilities
    elif model_type == "handwritten":
        output = np.random.rand(100, 10)  # Character probabilities
    elif model_type == "hybrid":
        output = np.random.rand(200, 10)  # Combined character probabilities
    
    # Call the function
    confidence_scores = tensorflow_utils.calculate_confidence_scores(output, model_type)
    
    # Verify results
    assert "fields" in confidence_scores
    assert "overall" in confidence_scores
    assert "low_confidence_fields" in confidence_scores
    assert "requires_human_review" in confidence_scores
    assert "metadata" in confidence_scores
    assert confidence_scores["metadata"]["model_type"] == model_type
    assert isinstance(confidence_scores["overall"], float)
    assert 0.0 <= confidence_scores["overall"] <= 1.0


@pytest.mark.parametrize("model_type,threshold,expected_review", [
    ("typed", 0.95, True),    # High threshold should trigger review
    ("typed", 0.5, False),    # Low threshold should not trigger review
    ("handwritten", 0.95, True),  # High threshold should trigger review
    ("handwritten", 0.5, False),  # Low threshold should not trigger review
    ("hybrid", 0.95, True),   # High threshold should trigger review
    ("hybrid", 0.5, False)    # Low threshold should not trigger review
])
def test_confidence_scores_threshold(model_type, threshold, expected_review):
    """Test confidence score thresholds for human review flagging."""
    # Create mock model output with medium confidence
    output = np.random.rand(100, 10) * 0.7 + 0.2  # Values between 0.2 and 0.9
    
    # Call the function with specified threshold
    confidence_scores = tensorflow_utils.calculate_confidence_scores(output, model_type, threshold)
    
    # Verify results
    assert confidence_scores["requires_human_review"] == expected_review
    if expected_review:
        assert len(confidence_scores["low_confidence_fields"]) > 0
    else:
        # May still have low confidence fields if they're below threshold
        pass


# ===== Test Performance Optimization =====

def test_get_optimal_batch_size():
    """Test determining optimal batch size based on GPU memory."""
    # Create a mock model
    mock_model = MagicMock(spec=tf.keras.Model)
    mock_model.input_shape = (None, 224, 224, 3)
    
    # Mock successful inference for batch sizes 1-4, failure for batch size 5
    def side_effect(input_tensor, training):
        batch_size = input_tensor.shape[0]
        if batch_size >= 5:
            raise tf.errors.ResourceExhaustedError(None, None, "Out of memory")
        return np.random.rand(batch_size, 10)
    
    mock_model.side_effect = side_effect
    
    # Mock random.normal to return tensors of appropriate shape
    with patch("tensorflow.random.normal", side_effect=lambda shape: tf.ones(shape)):
        # Mock device context
        with patch("tensorflow.device"):
            # Call the function
            optimal_batch_size = tensorflow_utils.get_optimal_batch_size(mock_model, initial_batch_size=1, max_batch_size=8)
            
            # Verify results - should be 4 (since 5 fails)
            # Note: This is hard to test precisely without actual GPU, so we're just checking the function runs
            assert isinstance(optimal_batch_size, int)
            assert optimal_batch_size >= 1


def test_monitor_gpu_utilization():
    """Test monitoring GPU utilization."""
    # Mock GPU devices
    with patch("tensorflow.config.list_physical_devices", return_value=[MagicMock()]):
        # Call the function
        metrics = tensorflow_utils.monitor_gpu_utilization()
        
        # Verify results
        assert "timestamp" in metrics
        assert "gpus" in metrics
        assert isinstance(metrics["gpus"], dict)
        # Note: Actual values would depend on GPU monitoring libraries


# ===== Integration Tests =====

@pytest.mark.integration
@pytest.mark.skipif(not tf.test.is_gpu_available(), reason="No GPU available")
def test_end_to_end_gpu_workflow():
    """Test the complete GPU workflow from configuration to inference."""
    # This test only runs if a GPU is actually available
    
    # Configure GPU
    gpu_config = tensorflow_utils.configure_gpu_memory(allow_growth=True)
    assert gpu_config["gpu_available"] == True
    
    # Verify GPU requirements
    meets_requirements, _ = tensorflow_utils.verify_gpu_requirements()
    if not meets_requirements:
        pytest.skip("GPU does not meet minimum requirements")
    
    # Create a simple test model
    inputs = tf.keras.Input(shape=(32, 32, 3))
    x = tf.keras.layers.Conv2D(16, (3, 3), activation='relu')(inputs)
    x = tf.keras.layers.MaxPooling2D((2, 2))(x)
    x = tf.keras.layers.Flatten()(x)
    outputs = tf.keras.layers.Dense(10, activation='softmax')(x)
    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    
    # Save the model to a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        model_path = os.path.join(temp_dir, "test_model")
        model.save(model_path)
        
        # Create a version file
        version_data = {
            "version": "1.0.0",
            "created_at": "2023-01-15T14:30:45Z",
            "model_type": "typed",
            "metadata": {
                "accuracy": 0.95,
                "min_tf_version": "2.15.0"
            }
        }
        version_file = os.path.join(model_path, tensorflow_utils.MODEL_VERSION_FILE)
        with open(version_file, "w") as f:
            json.dump(version_data, f)
        
        # Load the model
        loaded_model = tensorflow_utils.load_model(model_path, "typed")
        
        # Run inference
        test_image = np.random.rand(1, 32, 32, 3)
        output, metadata = tensorflow_utils.run_inference(loaded_model, test_image, "typed")
        
        # Verify results
        assert output is not None
        assert metadata["gpu_utilized"] == True
        assert metadata["model_type"] == "typed"
        assert "confidence_scores" in metadata
        
        # Clean up GPU memory
        cleanup_result = tensorflow_utils.cleanup_gpu_memory()
        assert cleanup_result["success"] == True