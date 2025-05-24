"""Unit tests for the tensorflow_utils.py module.

This module contains tests for TensorFlow model loading, inference, GPU resource
management, model versioning, and performance monitoring to ensure effective OCR
functionality using TensorFlow models.
"""

import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest
import numpy as np
import tensorflow as tf

# Import the module to test
import sys
import importlib.util
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent.parent.parent / 'src'
sys.path.insert(0, str(src_path))

# Import the module to test
from utils.tensorflow_utils import (
    configure_gpu_memory,
    get_available_gpu_memory,
    check_gpu_requirements,
    get_model_version,
    validate_model_compatibility,
    load_model,
    load_all_models,
    preprocess_image_for_ocr,
    run_inference,
    calculate_confidence_scores,
    get_field_confidence,
    monitor_gpu_utilization,
    optimize_model_for_inference,
    get_model_metadata
)


# ===== GPU Configuration and Memory Management Tests =====

@pytest.mark.parametrize("memory_limit", [0.5, 0.8, 0.9, 1.0])
def test_configure_gpu_memory(memory_limit, mock_logger):
    """Test GPU memory configuration with different memory limits."""
    with patch("tensorflow.config.list_physical_devices") as mock_list_devices, \
         patch("tensorflow.config.experimental.set_memory_growth") as mock_set_growth, \
         patch("tensorflow.config.experimental.get_memory_info") as mock_get_memory_info, \
         patch("tensorflow.config.set_logical_device_configuration") as mock_set_config:
        
        # Mock GPU devices
        mock_gpu = MagicMock()
        mock_gpu.name = "GPU:0"
        mock_list_devices.return_value = [mock_gpu]
        
        # Mock memory info
        mock_get_memory_info.return_value = {"total": 8 * (1024**3), "used": 1 * (1024**3)}  # 8GB total, 1GB used
        
        # Call the function
        configure_gpu_memory(memory_limit)
        
        # Verify function calls
        mock_list_devices.assert_called_once_with('GPU')
        mock_set_growth.assert_called_once_with(mock_gpu, True)
        
        if memory_limit < 1.0:
            mock_get_memory_info.assert_called_once_with(mock_gpu)
            mock_set_config.assert_called_once()
        else:
            # For memory_limit=1.0, we shouldn't set specific memory limits
            mock_set_config.assert_not_called()


def test_configure_gpu_memory_no_gpu(mock_logger):
    """Test GPU memory configuration when no GPU is available."""
    with patch("tensorflow.config.list_physical_devices") as mock_list_devices:
        # Mock no GPU devices
        mock_list_devices.return_value = []
        
        # Call the function
        configure_gpu_memory()
        
        # Verify warning was logged
        mock_logger.warning.assert_called_once_with("No GPU found. Running on CPU which will be significantly slower.")


def test_get_available_gpu_memory(mock_logger):
    """Test getting available GPU memory."""
    with patch("tensorflow.config.list_physical_devices") as mock_list_devices, \
         patch("tensorflow.config.experimental.get_memory_info") as mock_get_memory_info:
        
        # Mock GPU devices
        mock_gpu1 = MagicMock()
        mock_gpu1.name = "GPU:0"
        mock_gpu2 = MagicMock()
        mock_gpu2.name = "GPU:1"
        mock_list_devices.return_value = [mock_gpu1, mock_gpu2]
        
        # Mock memory info for each GPU
        def mock_memory_info(gpu):
            if gpu.name == "GPU:0":
                return {"total": 8 * (1024**3), "used": 2 * (1024**3)}  # 8GB total, 2GB used
            else:
                return {"total": 16 * (1024**3), "used": 4 * (1024**3)}  # 16GB total, 4GB used
        
        mock_get_memory_info.side_effect = mock_memory_info
        
        # Call the function
        memory_info = get_available_gpu_memory()
        
        # Verify results
        assert "GPU:0" in memory_info
        assert "GPU:1" in memory_info
        assert memory_info["GPU:0"] == 6.0  # 8GB - 2GB = 6GB
        assert memory_info["GPU:1"] == 12.0  # 16GB - 4GB = 12GB


def test_get_available_gpu_memory_error(mock_logger):
    """Test error handling when getting GPU memory fails."""
    with patch("tensorflow.config.list_physical_devices") as mock_list_devices, \
         patch("tensorflow.config.experimental.get_memory_info") as mock_get_memory_info:
        
        # Mock GPU devices
        mock_gpu = MagicMock()
        mock_gpu.name = "GPU:0"
        mock_list_devices.return_value = [mock_gpu]
        
        # Mock memory info to raise an exception
        mock_get_memory_info.side_effect = RuntimeError("Memory info not available")
        
        # Call the function
        memory_info = get_available_gpu_memory()
        
        # Verify results
        assert "GPU:0" in memory_info
        assert memory_info["GPU:0"] == -1.0  # Error indicator
        mock_logger.warning.assert_called_once()


def test_check_gpu_requirements_success(mock_logger):
    """Test GPU requirements check when requirements are met."""
    with patch("tensorflow.config.list_physical_devices") as mock_list_devices, \
         patch("tensorflow.test.is_built_with_cuda") as mock_is_cuda, \
         patch("ocr_service.utils.tensorflow_utils.get_available_gpu_memory") as mock_get_memory:
        
        # Mock GPU devices
        mock_gpu = MagicMock()
        mock_gpu.name = "GPU:0"
        mock_list_devices.return_value = [mock_gpu]
        
        # Mock CUDA availability
        mock_is_cuda.return_value = True
        
        # Mock memory info
        mock_get_memory.return_value = {"GPU:0": 10.0}  # 10GB available
        
        # Call the function with 8GB requirement
        result = check_gpu_requirements(min_vram_gb=8.0)
        
        # Verify results
        assert result is True


def test_check_gpu_requirements_failure_no_gpu(mock_logger):
    """Test GPU requirements check when no GPU is available."""
    with patch("tensorflow.config.list_physical_devices") as mock_list_devices:
        # Mock no GPU devices
        mock_list_devices.return_value = []
        
        # Call the function
        result = check_gpu_requirements()
        
        # Verify results
        assert result is False
        mock_logger.warning.assert_called_once_with("No GPU found. OCR processing requires GPU acceleration.")


def test_check_gpu_requirements_failure_no_cuda(mock_logger):
    """Test GPU requirements check when CUDA is not available."""
    with patch("tensorflow.config.list_physical_devices") as mock_list_devices, \
         patch("tensorflow.test.is_built_with_cuda") as mock_is_cuda:
        
        # Mock GPU devices
        mock_gpu = MagicMock()
        mock_gpu.name = "GPU:0"
        mock_list_devices.return_value = [mock_gpu]
        
        # Mock CUDA unavailability
        mock_is_cuda.return_value = False
        
        # Call the function
        result = check_gpu_requirements()
        
        # Verify results
        assert result is False
        mock_logger.warning.assert_called_once_with("TensorFlow not built with CUDA support. OCR performance will be degraded.")


def test_check_gpu_requirements_failure_insufficient_vram(mock_logger):
    """Test GPU requirements check when VRAM is insufficient."""
    with patch("tensorflow.config.list_physical_devices") as mock_list_devices, \
         patch("tensorflow.test.is_built_with_cuda") as mock_is_cuda, \
         patch("ocr_service.utils.tensorflow_utils.get_available_gpu_memory") as mock_get_memory:
        
        # Mock GPU devices
        mock_gpu = MagicMock()
        mock_gpu.name = "GPU:0"
        mock_list_devices.return_value = [mock_gpu]
        
        # Mock CUDA availability
        mock_is_cuda.return_value = True
        
        # Mock memory info
        mock_get_memory.return_value = {"GPU:0": 4.0}  # 4GB available
        
        # Call the function with 8GB requirement
        result = check_gpu_requirements(min_vram_gb=8.0)
        
        # Verify results
        assert result is False
        mock_logger.warning.assert_called_once()


# ===== Model Loading and Versioning Tests =====

def test_get_model_version_success(temp_dir, mock_logger):
    """Test getting model version information when version file exists."""
    # Create a temporary model version file
    version_info = {
        "version": "1.2.3",
        "date_trained": "2025-05-01",
        "accuracy": 0.95,
        "framework_version": "2.15.0"
    }
    
    version_file = temp_dir / "model_version.json"
    with open(version_file, 'w') as f:
        json.dump(version_info, f)
    
    # Call the function
    result = get_model_version(str(temp_dir))
    
    # Verify results
    assert result == version_info


def test_get_model_version_no_file(temp_dir, mock_logger):
    """Test getting model version information when version file doesn't exist."""
    # Call the function with a directory that doesn't have a version file
    result = get_model_version(str(temp_dir))
    
    # Verify results
    assert result["version"] == "unknown"
    assert result["date_trained"] == "unknown"
    assert result["accuracy"] == "unknown"
    assert result["framework_version"] == "unknown"
    mock_logger.warning.assert_called_once()


def test_get_model_version_error(temp_dir, mock_logger):
    """Test error handling when reading model version fails."""
    with patch("builtins.open", mock_open()) as mock_file:
        # Mock open to raise an exception
        mock_file.side_effect = IOError("Failed to open file")
        
        # Call the function
        result = get_model_version(str(temp_dir))
        
        # Verify results
        assert result["version"] == "error"
        assert result["date_trained"] == "error"
        assert result["accuracy"] == "error"
        assert result["framework_version"] == "error"
        assert "error" in result
        mock_logger.error.assert_called_once()


def test_validate_model_compatibility_success(temp_dir, mock_logger):
    """Test model compatibility validation when model is compatible."""
    # Create a temporary model version file with matching TF version
    version_info = {
        "version": "1.2.3",
        "date_trained": "2025-05-01",
        "accuracy": 0.95,
        "framework_version": tf.__version__  # Use current TF version
    }
    
    version_file = temp_dir / "model_version.json"
    with open(version_file, 'w') as f:
        json.dump(version_info, f)
    
    # Call the function
    result = validate_model_compatibility(str(temp_dir))
    
    # Verify results
    assert result is True


def test_validate_model_compatibility_incompatible(temp_dir, mock_logger):
    """Test model compatibility validation when model is incompatible."""
    # Get current TF version
    current_version = tf.__version__
    major_version = int(current_version.split('.')[0])
    
    # Create a temporary model version file with incompatible TF version
    version_info = {
        "version": "1.2.3",
        "date_trained": "2025-05-01",
        "accuracy": 0.95,
        "framework_version": f"{major_version + 1}.0.0"  # Incompatible major version
    }
    
    version_file = temp_dir / "model_version.json"
    with open(version_file, 'w') as f:
        json.dump(version_info, f)
    
    # Call the function
    result = validate_model_compatibility(str(temp_dir))
    
    # Verify results
    assert result is False
    assert mock_logger.warning.call_count == 2


def test_load_model_success(temp_dir, tf_model_mock, mock_logger):
    """Test loading a TensorFlow model successfully."""
    # Create model subdirectory
    model_type = "typed"
    model_dir = temp_dir / model_type
    model_dir.mkdir()
    
    # Create a version file
    version_info = {
        "version": "1.2.3",
        "date_trained": "2025-05-01",
        "accuracy": 0.95,
        "framework_version": tf.__version__
    }
    
    version_file = model_dir / "model_version.json"
    with open(version_file, 'w') as f:
        json.dump(version_info, f)
    
    with patch("ocr_service.utils.tensorflow_utils.validate_model_compatibility") as mock_validate:
        # Mock validation to return True
        mock_validate.return_value = True
        
        # Call the function
        model = load_model(str(temp_dir), model_type)
        
        # Verify results
        assert model is not None
        assert model == tf_model_mock
        mock_logger.info.assert_called()


def test_load_model_invalid_type(mock_logger):
    """Test loading a model with an invalid model type."""
    # Call the function with an invalid model type
    model = load_model("/path/to/models", "invalid_type")
    
    # Verify results
    assert model is None
    mock_logger.error.assert_called_once()


def test_load_model_not_found(temp_dir, mock_logger):
    """Test loading a model that doesn't exist."""
    # Call the function with a non-existent model path
    model = load_model(str(temp_dir), "typed")
    
    # Verify results
    assert model is None
    mock_logger.error.assert_called_once()


def test_load_all_models(temp_dir, tf_model_mock, mock_logger):
    """Test loading all models."""
    # Create model subdirectories
    for model_type in ["typed", "handwritten", "hybrid", "structure"]:
        model_dir = temp_dir / model_type
        model_dir.mkdir()
        
        # Create a version file
        version_info = {
            "version": "1.2.3",
            "date_trained": "2025-05-01",
            "accuracy": 0.95,
            "framework_version": tf.__version__
        }
        
        version_file = model_dir / "model_version.json"
        with open(version_file, 'w') as f:
            json.dump(version_info, f)
    
    with patch("ocr_service.utils.tensorflow_utils.load_model") as mock_load_model:
        # Mock load_model to return the mock model
        mock_load_model.return_value = tf_model_mock
        
        # Call the function
        models = load_all_models(str(temp_dir))
        
        # Verify results
        assert len(models) == 4
        assert all(model_type in models for model_type in ["typed", "handwritten", "hybrid", "structure"])
        assert all(model == tf_model_mock for model in models.values())
        assert mock_load_model.call_count == 4
        mock_logger.info.assert_called_with(f"Successfully loaded 4 OCR models")


# ===== Image Preprocessing Tests =====

def test_preprocess_image_for_ocr_typed():
    """Test image preprocessing for typed text OCR."""
    # Create a test image
    image = np.random.rand(500, 600, 3).astype(np.uint8)
    
    with patch("tensorflow.image.resize") as mock_resize, \
         patch("tensorflow.image.per_image_standardization") as mock_standardize:
        
        # Mock resize to return the input
        mock_resize.return_value = image.astype(np.float32) / 255.0
        # Mock standardize to return the input
        mock_standardize.return_value = image.astype(np.float32) / 255.0
        
        # Call the function
        result = preprocess_image_for_ocr(image, "typed")
        
        # Verify function calls
        mock_resize.assert_called_once_with(image.astype(np.float32) / 255.0, [768, 1024])
        mock_standardize.assert_called_once()
        
        # Verify result shape (should have batch dimension)
        assert len(result.shape) == 4
        assert result.shape[0] == 1  # Batch dimension


def test_preprocess_image_for_ocr_handwritten():
    """Test image preprocessing for handwritten text OCR."""
    # Create a test image
    image = np.random.rand(500, 600, 3).astype(np.uint8)
    
    with patch("tensorflow.image.resize") as mock_resize:
        # Mock resize to return the input
        mock_resize.return_value = image.astype(np.float32) / 255.0
        
        # Call the function
        result = preprocess_image_for_ocr(image, "handwritten")
        
        # Verify function calls
        mock_resize.assert_called_once_with(image.astype(np.float32) / 255.0, [800, 1280])
        
        # Verify result shape (should have batch dimension)
        assert len(result.shape) == 4
        assert result.shape[0] == 1  # Batch dimension


def test_preprocess_image_for_ocr_hybrid():
    """Test image preprocessing for hybrid text OCR."""
    # Create a test image
    image = np.random.rand(500, 600, 3).astype(np.uint8)
    
    with patch("tensorflow.image.resize") as mock_resize, \
         patch("tensorflow.image.per_image_standardization") as mock_standardize:
        
        # Mock resize to return the input
        mock_resize.return_value = image.astype(np.float32) / 255.0
        # Mock standardize to return the input
        mock_standardize.return_value = image.astype(np.float32) / 255.0
        
        # Call the function
        result = preprocess_image_for_ocr(image, "hybrid")
        
        # Verify function calls
        mock_resize.assert_called_once_with(image.astype(np.float32) / 255.0, [800, 1280])
        mock_standardize.assert_called_once()
        
        # Verify result shape (should have batch dimension)
        assert len(result.shape) == 4
        assert result.shape[0] == 1  # Batch dimension


def test_preprocess_image_for_ocr_structure():
    """Test image preprocessing for structure recognition."""
    # Create a test image
    image = np.random.rand(500, 600, 3).astype(np.uint8)
    
    with patch("tensorflow.image.resize") as mock_resize:
        # Mock resize to return a numpy array
        resized_image = np.random.rand(400, 500, 3).astype(np.float32)
        mock_resize.return_value = resized_image
        
        # Call the function
        result = preprocess_image_for_ocr(image, "structure")
        
        # Verify function calls
        mock_resize.assert_called_once()
        
        # Verify result shape (should have batch dimension)
        assert len(result.shape) == 4
        assert result.shape[0] == 1  # Batch dimension
        assert result.shape[1] == 1600  # Target size
        assert result.shape[2] == 1600  # Target size


def test_preprocess_image_for_ocr_invalid_type(mock_logger):
    """Test image preprocessing with an invalid model type."""
    # Create a test image
    image = np.random.rand(500, 600, 3).astype(np.uint8)
    
    # Call the function with an invalid model type
    result = preprocess_image_for_ocr(image, "invalid_type")
    
    # Verify error was logged
    mock_logger.error.assert_called_once()
    
    # Verify result shape (should have batch dimension)
    assert len(result.shape) == 4
    assert result.shape[0] == 1  # Batch dimension


# ===== Model Inference Tests =====

def test_run_inference_success(tf_model_mock):
    """Test running inference successfully."""
    # Create a test image with batch dimension
    image = np.random.rand(1, 500, 600, 3).astype(np.float32)
    
    # Mock model predict to return a specific output
    expected_output = np.random.rand(1, 50, 94)  # Example output shape
    tf_model_mock.predict.return_value = expected_output
    
    # Call the function
    output, inference_time = run_inference(tf_model_mock, image)
    
    # Verify results
    assert output is not None
    assert np.array_equal(output, expected_output)
    assert inference_time > 0.0
    tf_model_mock.predict.assert_called_once_with(image)


def test_run_inference_without_batch_dimension(tf_model_mock):
    """Test running inference on an image without batch dimension."""
    # Create a test image without batch dimension
    image = np.random.rand(500, 600, 3).astype(np.float32)
    
    # Mock model predict to return a specific output
    expected_output = np.random.rand(1, 50, 94)  # Example output shape
    tf_model_mock.predict.return_value = expected_output
    
    # Call the function
    output, inference_time = run_inference(tf_model_mock, image)
    
    # Verify results
    assert output is not None
    assert np.array_equal(output, expected_output)
    assert inference_time > 0.0
    # Verify that predict was called with an image that has batch dimension
    args, _ = tf_model_mock.predict.call_args
    assert len(args[0].shape) == 4
    assert args[0].shape[0] == 1  # Batch dimension


def test_run_inference_error(tf_model_mock, mock_logger):
    """Test error handling during inference."""
    # Create a test image
    image = np.random.rand(1, 500, 600, 3).astype(np.float32)
    
    # Mock model predict to raise an exception
    tf_model_mock.predict.side_effect = RuntimeError("Inference failed")
    
    # Call the function
    output, inference_time = run_inference(tf_model_mock, image)
    
    # Verify results
    assert output is None
    assert inference_time == 0.0
    mock_logger.error.assert_called_once()


# ===== Confidence Scoring Tests =====

@pytest.mark.parametrize("model_type,expected_keys", [
    ("typed", ["overall", "text_recognition", "field_extraction"]),
    ("handwritten", ["overall", "text_recognition", "field_extraction"]),
    ("hybrid", ["overall", "text_recognition", "field_extraction"]),
    ("structure", ["overall", "layout_detection", "table_recognition", "form_field_detection"])
])
def test_calculate_confidence_scores(model_type, expected_keys):
    """Test calculating confidence scores for different model types."""
    # Create a mock model output
    model_output = np.random.rand(1, 50, 94)  # Example output shape
    
    # Call the function
    confidence_scores = calculate_confidence_scores(model_output, model_type)
    
    # Verify results
    assert all(key in confidence_scores for key in expected_keys)
    assert all(0.0 <= score <= 1.0 for score in confidence_scores.values())


def test_calculate_confidence_scores_unknown_type(mock_logger):
    """Test calculating confidence scores for an unknown model type."""
    # Create a mock model output
    model_output = np.random.rand(1, 50, 94)  # Example output shape
    
    # Call the function with an unknown model type
    confidence_scores = calculate_confidence_scores(model_output, "unknown_type")
    
    # Verify results
    assert "overall" in confidence_scores
    assert confidence_scores["overall"] == 0.5  # Default fallback
    mock_logger.warning.assert_called_once()


def test_calculate_confidence_scores_error(mock_logger):
    """Test error handling when calculating confidence scores."""
    # Create a mock model output that will cause an error
    model_output = "invalid_output"  # Not a numpy array
    
    # Call the function
    confidence_scores = calculate_confidence_scores(model_output, "typed")
    
    # Verify results
    assert "overall" in confidence_scores
    assert confidence_scores["overall"] == 0.0
    assert "error" in confidence_scores
    mock_logger.error.assert_called_once()


@pytest.mark.parametrize("field_value,model_type,expected_range", [
    ("ABC123", "typed", (0.9, 1.0)),  # Short alphanumeric field, typed
    ("123456", "typed", (0.9, 1.0)),  # Numeric field, typed
    ("ABC123", "handwritten", (0.8, 0.9)),  # Short alphanumeric field, handwritten
    ("Very long text with many characters and some special symbols like @#$%", "typed", (0.7, 0.9)),  # Long field with special chars
    ("", "typed", (0.0, 0.0))  # Empty field
])
def test_get_field_confidence(field_value, model_type, expected_range):
    """Test getting confidence score for a specific field."""
    # Create a mock model output
    model_output = np.random.rand(1, 50, 94)  # Example output shape
    
    # Call the function
    confidence = get_field_confidence("test_field", field_value, model_output, model_type)
    
    # Verify results
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0
    min_expected, max_expected = expected_range
    assert min_expected <= confidence <= max_expected


def test_get_field_confidence_error(mock_logger):
    """Test error handling when getting field confidence."""
    # Create a mock model output
    model_output = np.random.rand(1, 50, 94)  # Example output shape
    
    # Mock a function to raise an exception
    with patch("builtins.len") as mock_len:
        mock_len.side_effect = TypeError("Object has no len()")
        
        # Call the function
        confidence = get_field_confidence("test_field", "test_value", model_output, "typed")
        
        # Verify results
        assert confidence == 0.5  # Default medium confidence on error
        mock_logger.error.assert_called_once()


# ===== GPU Utilization Monitoring Tests =====

def test_monitor_gpu_utilization_with_pynvml():
    """Test monitoring GPU utilization with pynvml available."""
    with patch.dict("sys.modules", {"pynvml": MagicMock()}):
        # Mock pynvml functions
        pynvml = sys.modules["pynvml"]
        pynvml.nvmlInit = MagicMock()
        pynvml.nvmlDeviceGetCount = MagicMock(return_value=2)
        
        # Mock device handles
        mock_handle1 = MagicMock()
        mock_handle2 = MagicMock()
        pynvml.nvmlDeviceGetHandleByIndex = MagicMock(side_effect=[mock_handle1, mock_handle2])
        
        # Mock device names
        pynvml.nvmlDeviceGetName = MagicMock(side_effect=[b"Tesla V100", b"Tesla V100"])
        
        # Mock memory info
        mock_memory1 = MagicMock()
        mock_memory1.used = 4 * (1024**3)  # 4GB used
        mock_memory1.total = 16 * (1024**3)  # 16GB total
        
        mock_memory2 = MagicMock()
        mock_memory2.used = 8 * (1024**3)  # 8GB used
        mock_memory2.total = 16 * (1024**3)  # 16GB total
        
        pynvml.nvmlDeviceGetMemoryInfo = MagicMock(side_effect=[mock_memory1, mock_memory2])
        
        # Mock utilization rates
        mock_util1 = MagicMock()
        mock_util1.gpu = 30  # 30% GPU utilization
        mock_util1.memory = 25  # 25% memory utilization
        
        mock_util2 = MagicMock()
        mock_util2.gpu = 80  # 80% GPU utilization
        mock_util2.memory = 50  # 50% memory utilization
        
        pynvml.nvmlDeviceGetUtilizationRates = MagicMock(side_effect=[mock_util1, mock_util2])
        
        # Mock shutdown
        pynvml.nvmlShutdown = MagicMock()
        
        # Call the function
        metrics = monitor_gpu_utilization()
        
        # Verify results
        assert "gpu_0" in metrics
        assert "gpu_1" in metrics
        assert metrics["gpu_0"]["memory_used_gb"] == 4.0
        assert metrics["gpu_0"]["memory_total_gb"] == 16.0
        assert metrics["gpu_0"]["memory_percent"] == 25.0
        assert metrics["gpu_0"]["gpu_utilization"] == 30
        assert metrics["gpu_1"]["memory_used_gb"] == 8.0
        assert metrics["gpu_1"]["memory_total_gb"] == 16.0
        assert metrics["gpu_1"]["memory_percent"] == 50.0
        assert metrics["gpu_1"]["gpu_utilization"] == 80


def test_monitor_gpu_utilization_without_pynvml():
    """Test monitoring GPU utilization without pynvml available."""
    with patch.dict("sys.modules", {"pynvml": None}), \
         patch("ocr_service.utils.tensorflow_utils.get_available_gpu_memory") as mock_get_memory:
        
        # Mock memory info
        mock_get_memory.return_value = {"GPU:0": 12.0, "GPU:1": 8.0}
        
        # Call the function
        metrics = monitor_gpu_utilization()
        
        # Verify results
        assert "memory_info" in metrics
        assert metrics["memory_info"] == {"GPU:0": 12.0, "GPU:1": 8.0}
        assert "note" in metrics


def test_monitor_gpu_utilization_error(mock_logger):
    """Test error handling when monitoring GPU utilization."""
    with patch.dict("sys.modules", {"pynvml": MagicMock()}):
        # Mock pynvml functions to raise an exception
        pynvml = sys.modules["pynvml"]
        pynvml.nvmlInit = MagicMock(side_effect=RuntimeError("NVML initialization failed"))
        
        # Call the function
        metrics = monitor_gpu_utilization()
        
        # Verify results
        assert "error" in metrics
        mock_logger.error.assert_called_once()


# ===== Model Optimization Tests =====

def test_optimize_model_for_inference_with_tensorrt(tf_model_mock, mock_logger):
    """Test optimizing a model with TensorRT."""
    with patch.dict("sys.modules", {"tensorflow.python.compiler.tensorrt": MagicMock()}):
        # Mock TensorRT module
        trt = sys.modules["tensorflow.python.compiler.tensorrt"].trt_convert
        
        # Mock TensorRT converter
        mock_converter = MagicMock()
        trt.TrtGraphConverterV2 = MagicMock(return_value=mock_converter)
        
        # Mock TensorRT precision mode
        trt.TrtPrecisionMode = MagicMock()
        trt.TrtPrecisionMode.FP16 = "FP16"
        
        # Mock saved_model.load
        with patch("tensorflow.saved_model.load") as mock_load:
            mock_optimized_model = MagicMock()
            mock_load.return_value = mock_optimized_model
            
            # Mock os.makedirs and shutil.rmtree
            with patch("os.makedirs") as mock_makedirs, \
                 patch("shutil.rmtree") as mock_rmtree:
                
                # Call the function
                optimized_model = optimize_model_for_inference(tf_model_mock)
                
                # Verify results
                assert optimized_model is not None
                assert isinstance(optimized_model, tf.keras.Model)
                mock_converter.convert.assert_called_once()
                mock_converter.save.assert_called_once()
                mock_load.assert_called_once()
                mock_logger.info.assert_called_with("Model successfully optimized with TensorRT")


def test_optimize_model_for_inference_without_tensorrt(tf_model_mock, mock_logger):
    """Test optimizing a model without TensorRT."""
    with patch.dict("sys.modules", {"tensorflow.python.compiler.tensorrt": None}), \
         patch("tensorflow.function") as mock_function, \
         patch("tensorflow.python.framework.convert_to_constants.convert_variables_to_constants_v2") as mock_convert:
        
        # Mock tf.function
        mock_function.return_value = MagicMock()
        mock_function.return_value.get_concrete_function = MagicMock()
        
        # Mock convert_variables_to_constants_v2
        mock_frozen_func = MagicMock()
        mock_frozen_func.inputs = [MagicMock()]
        mock_frozen_func.outputs = [MagicMock()]
        mock_convert.return_value = mock_frozen_func
        
        # Call the function
        optimized_model = optimize_model_for_inference(tf_model_mock)
        
        # Verify results
        assert optimized_model is not None
        assert isinstance(optimized_model, tf.keras.Model)
        mock_function.assert_called_once()
        mock_convert.assert_called_once()
        mock_logger.info.assert_called_with("Optimizing model with TensorFlow constant folding...")


def test_optimize_model_for_inference_error(tf_model_mock, mock_logger):
    """Test error handling when optimizing a model."""
    with patch("tensorflow.function") as mock_function:
        # Mock tf.function to raise an exception
        mock_function.side_effect = RuntimeError("Optimization failed")
        
        # Call the function
        optimized_model = optimize_model_for_inference(tf_model_mock)
        
        # Verify results
        assert optimized_model is not None
        assert optimized_model == tf_model_mock  # Should return original model on error
        mock_logger.error.assert_called_once()
        mock_logger.warning.assert_called_once_with("Returning original unoptimized model")


# ===== Model Metadata Tests =====

def test_get_model_metadata(tf_model_mock):
    """Test getting model metadata."""
    # Mock model properties
    mock_input = MagicMock()
    mock_input.name = "input_1"
    mock_input.shape.as_list.return_value = [None, 224, 224, 3]
    mock_input.dtype.name = "float32"
    
    mock_output = MagicMock()
    mock_output.name = "output_1"
    mock_output.shape.as_list.return_value = [None, 1000]
    mock_output.dtype.name = "float32"
    
    tf_model_mock.inputs = [mock_input]
    tf_model_mock.outputs = [mock_output]
    tf_model_mock.count_params.return_value = 25000000
    
    # Mock layers
    mock_layer1 = MagicMock()
    mock_layer1.name = "conv1"
    mock_layer1.__class__.__name__ = "Conv2D"
    mock_layer1.count_params.return_value = 9408
    mock_layer1.output_shape = (None, 112, 112, 64)
    
    mock_layer2 = MagicMock()
    mock_layer2.name = "pool1"
    mock_layer2.__class__.__name__ = "MaxPooling2D"
    mock_layer2.count_params.return_value = 0
    mock_layer2.output_shape = (None, 56, 56, 64)
    
    tf_model_mock.layers = [mock_layer1, mock_layer2]
    
    # Call the function
    metadata = get_model_metadata(tf_model_mock)
    
    # Verify results
    assert "input_shapes" in metadata
    assert "output_shapes" in metadata
    assert "parameter_count" in metadata
    assert "layers" in metadata
    
    assert len(metadata["input_shapes"]) == 1
    assert metadata["input_shapes"][0]["name"] == "input_1"
    assert metadata["input_shapes"][0]["shape"] == [None, 224, 224, 3]
    
    assert len(metadata["output_shapes"]) == 1
    assert metadata["output_shapes"][0]["name"] == "output_1"
    assert metadata["output_shapes"][0]["shape"] == [None, 1000]
    
    assert metadata["parameter_count"] == 25000000
    
    assert len(metadata["layers"]) == 2
    assert metadata["layers"][0]["name"] == "conv1"
    assert metadata["layers"][0]["type"] == "Conv2D"
    assert metadata["layers"][0]["parameters"] == 9408
    assert metadata["layers"][1]["name"] == "pool1"
    assert metadata["layers"][1]["type"] == "MaxPooling2D"
    assert metadata["layers"][1]["parameters"] == 0


def test_get_model_metadata_error(tf_model_mock, mock_logger):
    """Test error handling when getting model metadata."""
    # Mock model properties to raise an exception
    tf_model_mock.inputs = MagicMock(side_effect=AttributeError("'NoneType' object has no attribute 'inputs'"))
    
    # Call the function
    metadata = get_model_metadata(tf_model_mock)
    
    # Verify results
    assert "error" in metadata
    mock_logger.error.assert_called_once()