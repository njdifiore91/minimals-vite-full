#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the OCR Service's tensorflow_config.py module.

This module contains tests to verify that TensorFlow configuration correctly sets up
model architectures, hyperparameters, GPU acceleration settings, confidence thresholds,
and model paths. It ensures that OCR processing works correctly with proper model configuration.

Test coverage includes:
- TensorFlow model configuration with GPU acceleration
- Confidence threshold configuration
- Model architecture and hyperparameter configuration
- Model path and versioning configuration
- GPU memory allocation and optimization settings
- Document type to model mapping
- Field type to model mapping
- Configuration function validation
"""

import os
import pytest
from unittest.mock import patch, MagicMock
import logging
from typing import Dict, Any

# Import the module under test
from src.config.tensorflow_config import (
    get_tensorflow_config,
    get_model_config,
    get_model_path,
    get_model_type_for_document,
    get_model_type_for_field,
    get_gpu_optimization_settings,
    get_model_versioning_settings,
    get_performance_monitoring_settings,
    log_tensorflow_config,
    TENSORFLOW_VERSION,
    MODEL_BASE_PATH,
    TYPED_MODEL_PATH,
    HANDWRITTEN_MODEL_PATH,
    HYBRID_MODEL_PATH,
    USE_GPU,
    GPU_MEMORY_LIMIT,
    GPU_ALLOW_GROWTH,
    MIXED_PRECISION,
    CONFIDENCE_THRESHOLD,
    VERIFICATION_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
    MODEL_ARCHITECTURES,
    DOCUMENT_TYPE_MODEL_MAPPING,
    FIELD_TYPE_MODEL_MAPPING,
    GPU_OPTIMIZATION_SETTINGS,
    MODEL_VERSIONING_SETTINGS,
    PERFORMANCE_MONITORING_SETTINGS
)

# Import types for type checking
from src.types.config import TensorFlowConfig


# ===== Test Default Configuration Values =====

def test_tensorflow_version():
    """
    Test that the TensorFlow version is correctly set to 2.15.0 as specified in the technical specification.
    """
    assert TENSORFLOW_VERSION == "2.15.0", "TensorFlow version should be 2.15.0 as specified in section 3.2.2"


def test_default_model_paths():
    """
    Test that the default model paths are correctly set.
    """
    assert MODEL_BASE_PATH == "/models", "Default model base path should be /models"
    assert TYPED_MODEL_PATH.endswith("/typed_text_ocr"), "Typed model path should end with /typed_text_ocr"
    assert HANDWRITTEN_MODEL_PATH.endswith("/handwritten_text_ocr"), "Handwritten model path should end with /handwritten_text_ocr"
    assert HYBRID_MODEL_PATH.endswith("/hybrid_text_ocr"), "Hybrid model path should end with /hybrid_text_ocr"


def test_default_gpu_settings():
    """
    Test that the default GPU settings are correctly set for performance as specified in the technical specification.
    """
    assert USE_GPU is True, "GPU should be enabled by default as specified in section 3.2.3"
    assert GPU_MEMORY_LIMIT == 8192, "GPU memory limit should be 8GB (8192MB) as specified in section 3.2.3"
    assert GPU_ALLOW_GROWTH is True, "GPU memory growth should be enabled by default"
    assert MIXED_PRECISION is True, "Mixed precision should be enabled by default for performance"


def test_default_confidence_thresholds():
    """
    Test that the default confidence thresholds are correctly set for 99% data extraction accuracy.
    """
    assert 0.6 <= CONFIDENCE_THRESHOLD <= 0.7, "Default confidence threshold should be around 0.65"
    assert 0.7 <= VERIFICATION_THRESHOLD <= 0.8, "Verification threshold should be around 0.75"
    assert 0.45 <= LOW_CONFIDENCE_THRESHOLD <= 0.55, "Low confidence threshold should be around 0.50"
    
    # Verify the relationship between thresholds
    assert LOW_CONFIDENCE_THRESHOLD < CONFIDENCE_THRESHOLD < VERIFICATION_THRESHOLD, \
        "Thresholds should be in ascending order: LOW_CONFIDENCE < CONFIDENCE < VERIFICATION"


# ===== Test Model Architecture Configuration =====

def test_model_architectures_structure():
    """
    Test that the model architectures dictionary contains the required model types and parameters.
    """
    # Check that all required model types are present
    assert "typed" in MODEL_ARCHITECTURES, "Typed model architecture should be defined"
    assert "handwritten" in MODEL_ARCHITECTURES, "Handwritten model architecture should be defined"
    assert "hybrid" in MODEL_ARCHITECTURES, "Hybrid model architecture should be defined"
    
    # Check that each model has the required parameters
    required_params = [
        "name", "description", "architecture", "input_shape", "confidence_threshold",
        "verification_threshold", "low_confidence_threshold", "max_text_length",
        "beam_width", "batch_size", "preprocessing"
    ]
    
    for model_type, config in MODEL_ARCHITECTURES.items():
        for param in required_params:
            assert param in config, f"Model {model_type} is missing required parameter: {param}"


def test_typed_model_architecture():
    """
    Test that the typed model architecture is correctly configured.
    """
    typed_config = MODEL_ARCHITECTURES["typed"]
    
    assert typed_config["architecture"] == "CNN-LSTM-CTC", "Typed model should use CNN-LSTM-CTC architecture"
    assert typed_config["backbone"] == "resnet50", "Typed model should use ResNet50 backbone"
    assert typed_config["lstm_units"] == 256, "Typed model should have 256 LSTM units"
    assert typed_config["lstm_layers"] == 2, "Typed model should have 2 LSTM layers"
    
    # Check preprocessing settings
    assert typed_config["preprocessing"]["normalize"] is True, "Typed model should normalize input"
    assert typed_config["preprocessing"]["contrast_enhancement"] > 1.0, "Typed model should enhance contrast"


def test_handwritten_model_architecture():
    """
    Test that the handwritten model architecture is correctly configured.
    """
    handwritten_config = MODEL_ARCHITECTURES["handwritten"]
    
    assert handwritten_config["architecture"] == "CNN-BiLSTM-Attention", "Handwritten model should use CNN-BiLSTM-Attention architecture"
    assert handwritten_config["backbone"] == "efficientnetb3", "Handwritten model should use EfficientNetB3 backbone"
    assert handwritten_config["lstm_units"] == 512, "Handwritten model should have 512 LSTM units"
    assert handwritten_config["lstm_layers"] == 3, "Handwritten model should have 3 LSTM layers"
    assert "attention_units" in handwritten_config, "Handwritten model should have attention mechanism"
    
    # Check that handwritten model has lower confidence thresholds
    assert handwritten_config["confidence_threshold"] < MODEL_ARCHITECTURES["typed"]["confidence_threshold"], \
        "Handwritten model should have lower confidence threshold than typed model"


def test_hybrid_model_architecture():
    """
    Test that the hybrid model architecture is correctly configured.
    """
    hybrid_config = MODEL_ARCHITECTURES["hybrid"]
    
    assert hybrid_config["architecture"] == "CNN-Transformer", "Hybrid model should use CNN-Transformer architecture"
    assert hybrid_config["backbone"] == "efficientnetb4", "Hybrid model should use EfficientNetB4 backbone"
    assert "transformer_layers" in hybrid_config, "Hybrid model should have transformer layers"
    assert "transformer_heads" in hybrid_config, "Hybrid model should have transformer heads"
    assert "transformer_dim" in hybrid_config, "Hybrid model should have transformer dimension"


# ===== Test Document and Field Type Mappings =====

def test_document_type_model_mapping():
    """
    Test that document types are correctly mapped to appropriate model types.
    """
    # Check that all expected document types are present
    expected_document_types = [
        "APPLICATION_FORM", "TAX_RETURN", "BANK_STATEMENT", "INVOICE", 
        "ID_DOCUMENT", "HANDWRITTEN_NOTE", "BUSINESS_LICENSE", 
        "UTILITY_BILL", "FINANCIAL_STATEMENT", "CONTRACT", "DEFAULT"
    ]
    
    for doc_type in expected_document_types:
        assert doc_type in DOCUMENT_TYPE_MODEL_MAPPING, f"Document type {doc_type} should be mapped to a model type"
    
    # Check specific mappings for correctness
    assert DOCUMENT_TYPE_MODEL_MAPPING["APPLICATION_FORM"] == "hybrid", "Application forms should use hybrid model"
    assert DOCUMENT_TYPE_MODEL_MAPPING["TAX_RETURN"] == "typed", "Tax returns should use typed model"
    assert DOCUMENT_TYPE_MODEL_MAPPING["BANK_STATEMENT"] == "typed", "Bank statements should use typed model"
    assert DOCUMENT_TYPE_MODEL_MAPPING["HANDWRITTEN_NOTE"] == "handwritten", "Handwritten notes should use handwritten model"
    assert DOCUMENT_TYPE_MODEL_MAPPING["DEFAULT"] == "hybrid", "Default document type should use hybrid model"


def test_field_type_model_mapping():
    """
    Test that field types are correctly mapped to appropriate model types.
    """
    # Check that all expected field types are present
    expected_field_types = [
        "SIGNATURE", "CHECKBOX", "DATE", "AMOUNT", 
        "ACCOUNT_NUMBER", "NAME", "ADDRESS", "DEFAULT"
    ]
    
    for field_type in expected_field_types:
        assert field_type in FIELD_TYPE_MODEL_MAPPING, f"Field type {field_type} should be mapped to a model type"
    
    # Check specific mappings for correctness
    assert FIELD_TYPE_MODEL_MAPPING["SIGNATURE"] == "handwritten", "Signatures should use handwritten model"
    assert FIELD_TYPE_MODEL_MAPPING["CHECKBOX"] == "typed", "Checkboxes should use typed model"
    assert FIELD_TYPE_MODEL_MAPPING["ACCOUNT_NUMBER"] == "typed", "Account numbers should use typed model"
    assert FIELD_TYPE_MODEL_MAPPING["DEFAULT"] == "hybrid", "Default field type should use hybrid model"


# ===== Test GPU Optimization Settings =====

def test_gpu_optimization_settings():
    """
    Test that GPU optimization settings are correctly configured for performance.
    """
    # Check that all expected settings are present
    expected_settings = [
        "memory_growth", "memory_limit_mb", "mixed_precision", "xla_compilation",
        "inter_op_parallelism", "intra_op_parallelism", "gpu_per_process_memory_fraction",
        "allow_soft_placement", "log_device_placement", "jit_compilation"
    ]
    
    for setting in expected_settings:
        assert setting in GPU_OPTIMIZATION_SETTINGS, f"GPU optimization setting {setting} should be defined"
    
    # Check specific settings for correctness
    assert GPU_OPTIMIZATION_SETTINGS["memory_growth"] == GPU_ALLOW_GROWTH, \
        "memory_growth setting should match GPU_ALLOW_GROWTH"
    assert GPU_OPTIMIZATION_SETTINGS["memory_limit_mb"] == GPU_MEMORY_LIMIT, \
        "memory_limit_mb setting should match GPU_MEMORY_LIMIT"
    assert GPU_OPTIMIZATION_SETTINGS["mixed_precision"] == MIXED_PRECISION, \
        "mixed_precision setting should match MIXED_PRECISION"
    assert GPU_OPTIMIZATION_SETTINGS["xla_compilation"] is True, \
        "XLA compilation should be enabled for faster execution"
    assert GPU_OPTIMIZATION_SETTINGS["gpu_per_process_memory_fraction"] > 0.8, \
        "GPU memory fraction should be high for OCR processing"
    assert GPU_OPTIMIZATION_SETTINGS["allow_soft_placement"] is True, \
        "Soft placement should be enabled for flexibility"


def test_model_versioning_settings():
    """
    Test that model versioning settings are correctly configured.
    """
    # Check that all expected settings are present
    expected_settings = [
        "version_file", "min_tf_version", "check_compatibility", "version_format", "metadata_fields"
    ]
    
    for setting in expected_settings:
        assert setting in MODEL_VERSIONING_SETTINGS, f"Model versioning setting {setting} should be defined"
    
    # Check specific settings for correctness
    assert MODEL_VERSIONING_SETTINGS["min_tf_version"] == TENSORFLOW_VERSION, \
        "Minimum TensorFlow version should match the specified version"
    assert MODEL_VERSIONING_SETTINGS["check_compatibility"] is True, \
        "Version compatibility checking should be enabled"
    assert MODEL_VERSIONING_SETTINGS["version_format"] == "semver", \
        "Version format should be semantic versioning"
    
    # Check that required metadata fields are present
    required_metadata = ["model_type", "architecture", "accuracy", "created_at"]
    for field in required_metadata:
        assert field in MODEL_VERSIONING_SETTINGS["metadata_fields"], \
            f"Required metadata field {field} should be included"


def test_performance_monitoring_settings():
    """
    Test that performance monitoring settings are correctly configured.
    """
    # Check that all expected settings are present
    expected_settings = [
        "log_inference_time", "log_preprocessing_time", "log_postprocessing_time",
        "log_total_time", "log_gpu_utilization", "log_memory_usage",
        "performance_threshold_ms", "batch_size_optimization", "cleanup_gpu_memory"
    ]
    
    for setting in expected_settings:
        assert setting in PERFORMANCE_MONITORING_SETTINGS, f"Performance monitoring setting {setting} should be defined"
    
    # Check specific settings for correctness
    assert PERFORMANCE_MONITORING_SETTINGS["log_inference_time"] is True, \
        "Inference time logging should be enabled"
    assert PERFORMANCE_MONITORING_SETTINGS["log_total_time"] is True, \
        "Total processing time logging should be enabled"
    assert PERFORMANCE_MONITORING_SETTINGS["log_gpu_utilization"] is True, \
        "GPU utilization logging should be enabled"
    assert PERFORMANCE_MONITORING_SETTINGS["performance_threshold_ms"] > 0, \
        "Performance threshold should be positive"
    assert PERFORMANCE_MONITORING_SETTINGS["batch_size_optimization"] is True, \
        "Batch size optimization should be enabled"
    assert PERFORMANCE_MONITORING_SETTINGS["cleanup_gpu_memory"] is True, \
        "GPU memory cleanup should be enabled to prevent memory leaks"


# ===== Test Configuration Functions =====

def test_get_tensorflow_config():
    """
    Test that the get_tensorflow_config function returns a valid TensorFlowConfig object.
    """
    config = get_tensorflow_config()
    
    # Check that the returned object is a TensorFlowConfig
    assert isinstance(config, TensorFlowConfig), "get_tensorflow_config should return a TensorFlowConfig object"
    
    # Check that the config contains the expected values
    assert config.tensorflow_version == TENSORFLOW_VERSION, "TensorFlow version should match"
    assert config.model_base_path == MODEL_BASE_PATH, "Model base path should match"
    assert config.typed_model_path == TYPED_MODEL_PATH, "Typed model path should match"
    assert config.handwritten_model_path == HANDWRITTEN_MODEL_PATH, "Handwritten model path should match"
    assert config.hybrid_model_path == HYBRID_MODEL_PATH, "Hybrid model path should match"
    assert config.use_gpu == USE_GPU, "use_gpu setting should match"
    assert config.gpu_memory_limit == GPU_MEMORY_LIMIT, "gpu_memory_limit setting should match"
    assert config.gpu_allow_growth == GPU_ALLOW_GROWTH, "gpu_allow_growth setting should match"
    assert config.mixed_precision == MIXED_PRECISION, "mixed_precision setting should match"
    assert config.confidence_threshold == CONFIDENCE_THRESHOLD, "confidence_threshold setting should match"


def test_get_model_config():
    """
    Test that the get_model_config function returns the correct model configuration.
    """
    # Test with valid model types
    typed_config = get_model_config("typed")
    assert typed_config == MODEL_ARCHITECTURES["typed"], "get_model_config should return the typed model config"
    
    handwritten_config = get_model_config("handwritten")
    assert handwritten_config == MODEL_ARCHITECTURES["handwritten"], "get_model_config should return the handwritten model config"
    
    hybrid_config = get_model_config("hybrid")
    assert hybrid_config == MODEL_ARCHITECTURES["hybrid"], "get_model_config should return the hybrid model config"
    
    # Test with invalid model type
    with pytest.raises(ValueError):
        get_model_config("invalid_model_type")


def test_get_model_path():
    """
    Test that the get_model_path function returns the correct model path.
    """
    # Test with valid model types
    assert get_model_path("typed") == TYPED_MODEL_PATH, "get_model_path should return the typed model path"
    assert get_model_path("handwritten") == HANDWRITTEN_MODEL_PATH, "get_model_path should return the handwritten model path"
    assert get_model_path("hybrid") == HYBRID_MODEL_PATH, "get_model_path should return the hybrid model path"
    
    # Test with invalid model type
    with pytest.raises(ValueError):
        get_model_path("invalid_model_type")


def test_get_model_type_for_document():
    """
    Test that the get_model_type_for_document function returns the correct model type for a document type.
    """
    # Test with valid document types
    assert get_model_type_for_document("APPLICATION_FORM") == "hybrid", \
        "get_model_type_for_document should return 'hybrid' for APPLICATION_FORM"
    assert get_model_type_for_document("TAX_RETURN") == "typed", \
        "get_model_type_for_document should return 'typed' for TAX_RETURN"
    assert get_model_type_for_document("HANDWRITTEN_NOTE") == "handwritten", \
        "get_model_type_for_document should return 'handwritten' for HANDWRITTEN_NOTE"
    
    # Test with unknown document type (should return default)
    assert get_model_type_for_document("UNKNOWN_DOCUMENT_TYPE") == DOCUMENT_TYPE_MODEL_MAPPING["DEFAULT"], \
        "get_model_type_for_document should return the default model type for unknown document types"


def test_get_model_type_for_field():
    """
    Test that the get_model_type_for_field function returns the correct model type for a field type.
    """
    # Test with valid field types
    assert get_model_type_for_field("SIGNATURE") == "handwritten", \
        "get_model_type_for_field should return 'handwritten' for SIGNATURE"
    assert get_model_type_for_field("CHECKBOX") == "typed", \
        "get_model_type_for_field should return 'typed' for CHECKBOX"
    assert get_model_type_for_field("DATE") == "hybrid", \
        "get_model_type_for_field should return 'hybrid' for DATE"
    
    # Test with unknown field type (should return default)
    assert get_model_type_for_field("UNKNOWN_FIELD_TYPE") == FIELD_TYPE_MODEL_MAPPING["DEFAULT"], \
        "get_model_type_for_field should return the default model type for unknown field types"


def test_get_gpu_optimization_settings():
    """
    Test that the get_gpu_optimization_settings function returns the correct GPU optimization settings.
    """
    settings = get_gpu_optimization_settings()
    assert settings == GPU_OPTIMIZATION_SETTINGS, \
        "get_gpu_optimization_settings should return the GPU_OPTIMIZATION_SETTINGS dictionary"


def test_get_model_versioning_settings():
    """
    Test that the get_model_versioning_settings function returns the correct model versioning settings.
    """
    settings = get_model_versioning_settings()
    assert settings == MODEL_VERSIONING_SETTINGS, \
        "get_model_versioning_settings should return the MODEL_VERSIONING_SETTINGS dictionary"


def test_get_performance_monitoring_settings():
    """
    Test that the get_performance_monitoring_settings function returns the correct performance monitoring settings.
    """
    settings = get_performance_monitoring_settings()
    assert settings == PERFORMANCE_MONITORING_SETTINGS, \
        "get_performance_monitoring_settings should return the PERFORMANCE_MONITORING_SETTINGS dictionary"


# ===== Test Environment Variable Configuration =====

def test_env_var_model_paths(env_vars):
    """
    Test that model paths can be configured via environment variables.
    
    Args:
        env_vars: Fixture to set environment variables
    """
    # Set custom model paths via environment variables
    custom_base_path = "/custom/models"
    custom_typed_path = "/custom/models/typed"
    custom_handwritten_path = "/custom/models/handwritten"
    custom_hybrid_path = "/custom/models/hybrid"
    
    env_vars["OCR_MODEL_BASE_PATH"] = custom_base_path
    env_vars["OCR_TYPED_MODEL_PATH"] = custom_typed_path
    env_vars["OCR_HANDWRITTEN_MODEL_PATH"] = custom_handwritten_path
    env_vars["OCR_HYBRID_MODEL_PATH"] = custom_hybrid_path
    
    # Reload the module to apply environment variables
    with patch.dict(os.environ, env_vars):
        # Import the module again to reload with new environment variables
        from importlib import reload
        import src.config.tensorflow_config
        reload(src.config.tensorflow_config)
        
        # Check that the model paths were updated
        assert src.config.tensorflow_config.MODEL_BASE_PATH == custom_base_path
        assert src.config.tensorflow_config.TYPED_MODEL_PATH == custom_typed_path
        assert src.config.tensorflow_config.HANDWRITTEN_MODEL_PATH == custom_handwritten_path
        assert src.config.tensorflow_config.HYBRID_MODEL_PATH == custom_hybrid_path


def test_env_var_gpu_settings(env_vars):
    """
    Test that GPU settings can be configured via environment variables.
    
    Args:
        env_vars: Fixture to set environment variables
    """
    # Set custom GPU settings via environment variables
    env_vars["OCR_USE_GPU"] = "false"
    env_vars["OCR_GPU_MEMORY_LIMIT"] = "4096"
    env_vars["OCR_GPU_ALLOW_GROWTH"] = "false"
    env_vars["OCR_MIXED_PRECISION"] = "false"
    
    # Reload the module to apply environment variables
    with patch.dict(os.environ, env_vars):
        # Import the module again to reload with new environment variables
        from importlib import reload
        import src.config.tensorflow_config
        reload(src.config.tensorflow_config)
        
        # Check that the GPU settings were updated
        assert src.config.tensorflow_config.USE_GPU is False
        assert src.config.tensorflow_config.GPU_MEMORY_LIMIT == 4096
        assert src.config.tensorflow_config.GPU_ALLOW_GROWTH is False
        assert src.config.tensorflow_config.MIXED_PRECISION is False


def test_env_var_confidence_thresholds(env_vars):
    """
    Test that confidence thresholds can be configured via environment variables.
    
    Args:
        env_vars: Fixture to set environment variables
    """
    # Set custom confidence thresholds via environment variables
    env_vars["OCR_CONFIDENCE_THRESHOLD"] = "0.80"
    env_vars["OCR_VERIFICATION_THRESHOLD"] = "0.90"
    env_vars["OCR_LOW_CONFIDENCE_THRESHOLD"] = "0.60"
    
    # Reload the module to apply environment variables
    with patch.dict(os.environ, env_vars):
        # Import the module again to reload with new environment variables
        from importlib import reload
        import src.config.tensorflow_config
        reload(src.config.tensorflow_config)
        
        # Check that the confidence thresholds were updated
        assert src.config.tensorflow_config.CONFIDENCE_THRESHOLD == 0.80
        assert src.config.tensorflow_config.VERIFICATION_THRESHOLD == 0.90
        assert src.config.tensorflow_config.LOW_CONFIDENCE_THRESHOLD == 0.60


# ===== Test Logging Function =====

def test_log_tensorflow_config():
    """
    Test that the log_tensorflow_config function logs the TensorFlow configuration.
    """
    # Mock the logger
    with patch("src.config.tensorflow_config.logger") as mock_logger:
        # Call the function
        log_tensorflow_config()
        
        # Check that the logger was called with the expected messages
        assert mock_logger.info.call_count >= 10, "log_tensorflow_config should log multiple configuration settings"
        
        # Check that specific configuration settings were logged
        mock_logger.info.assert_any_call("TensorFlow Configuration:")
        
        # Check for specific configuration values in the log messages
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("TensorFlow Version" in call for call in log_calls)
        assert any("Model Base Path" in call for call in log_calls)
        assert any("Use GPU" in call for call in log_calls)
        assert any("GPU Memory Limit" in call for call in log_calls)
        assert any("Confidence Threshold" in call for call in log_calls)