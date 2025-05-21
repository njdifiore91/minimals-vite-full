#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TensorFlow Configuration for OCR Service

This module defines configuration parameters for the TensorFlow models used in OCR processing.
It specifies model architectures, hyperparameters, GPU acceleration settings, confidence thresholds,
and model paths. It ensures consistent model behavior across environments and enables accurate
text extraction from documents.

Key features:
- GPU memory allocation and optimization settings
- Model paths and versioning configuration
- Confidence thresholds for extracted fields
- Model architectures and hyperparameters
- Performance optimization settings

This configuration implements the requirements specified in the technical specification:
- OCR Service must use TensorFlow for text recognition (section 0.1.2)
- Service must use GPU acceleration for performance (section 3.2.3)
- OCR processing must include confidence scoring for extracted fields (section 0.1.2)
- Service must maintain 99% data extraction accuracy (section 0.1.1)
- Models must be versioned and configurable (section 0.2.3)
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from ..types.config import TensorFlowConfig
from ..utils.logging_utils import get_logger

# Configure logger
logger = get_logger(__name__)

# TensorFlow version (as specified in section 3.2.2)
TENSORFLOW_VERSION = "2.15.0"

# Base paths for models
MODEL_BASE_PATH = os.environ.get("OCR_MODEL_BASE_PATH", "/models")
TYPED_MODEL_PATH = os.environ.get("OCR_TYPED_MODEL_PATH", os.path.join(MODEL_BASE_PATH, "typed_text_ocr"))
HANDWRITTEN_MODEL_PATH = os.environ.get("OCR_HANDWRITTEN_MODEL_PATH", os.path.join(MODEL_BASE_PATH, "handwritten_text_ocr"))
HYBRID_MODEL_PATH = os.environ.get("OCR_HYBRID_MODEL_PATH", os.path.join(MODEL_BASE_PATH, "hybrid_text_ocr"))

# GPU settings (as specified in section 3.2.3)
USE_GPU = os.environ.get("OCR_USE_GPU", "true").lower() == "true"
GPU_MEMORY_LIMIT = int(os.environ.get("OCR_GPU_MEMORY_LIMIT", "8192"))  # 8GB VRAM as specified in section 3.2.3
GPU_ALLOW_GROWTH = os.environ.get("OCR_GPU_ALLOW_GROWTH", "true").lower() == "true"
MIXED_PRECISION = os.environ.get("OCR_MIXED_PRECISION", "true").lower() == "true"

# Thread parallelism settings
INTER_OP_PARALLELISM_THREADS = int(os.environ.get("OCR_INTER_OP_PARALLELISM_THREADS", "4"))
INTRA_OP_PARALLELISM_THREADS = int(os.environ.get("OCR_INTRA_OP_PARALLELISM_THREADS", "4"))

# Confidence thresholds (for 99% data extraction accuracy as specified in section 0.1.1)
CONFIDENCE_THRESHOLD = float(os.environ.get("OCR_CONFIDENCE_THRESHOLD", "0.65"))  # Default threshold for field extraction
VERIFICATION_THRESHOLD = float(os.environ.get("OCR_VERIFICATION_THRESHOLD", "0.75"))  # Threshold for automatic verification
LOW_CONFIDENCE_THRESHOLD = float(os.environ.get("OCR_LOW_CONFIDENCE_THRESHOLD", "0.50"))  # Threshold for human review

# Model parameters
MAX_TEXT_LENGTH = int(os.environ.get("OCR_MAX_TEXT_LENGTH", "768"))  # Maximum text length for recognition
BEAM_WIDTH = int(os.environ.get("OCR_BEAM_WIDTH", "10"))  # Beam width for text recognition
BATCH_SIZE = int(os.environ.get("OCR_BATCH_SIZE", "1"))  # Default batch size for inference

# Input preprocessing
INPUT_HEIGHT = int(os.environ.get("OCR_INPUT_HEIGHT", "1280"))
INPUT_WIDTH = int(os.environ.get("OCR_INPUT_WIDTH", "1280"))
INPUT_CHANNELS = int(os.environ.get("OCR_INPUT_CHANNELS", "3"))
NORMALIZE_INPUT = os.environ.get("OCR_NORMALIZE_INPUT", "true").lower() == "true"

# Model architecture settings
MODEL_ARCHITECTURES = {
    "typed": {
        "name": "typed_text_recognition",
        "description": "Model for recognizing typed/printed text in documents",
        "architecture": "CNN-LSTM-CTC",  # Convolutional Neural Network with LSTM and CTC loss
        "input_shape": (INPUT_HEIGHT, INPUT_WIDTH, INPUT_CHANNELS),
        "backbone": "resnet50",  # Feature extraction backbone
        "lstm_units": 256,  # Number of LSTM units
        "lstm_layers": 2,  # Number of LSTM layers
        "dropout_rate": 0.25,  # Dropout rate for regularization
        "learning_rate": 0.001,  # Initial learning rate
        "optimizer": "adam",  # Optimizer algorithm
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "verification_threshold": VERIFICATION_THRESHOLD,
        "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
        "max_text_length": MAX_TEXT_LENGTH,
        "beam_width": BEAM_WIDTH,
        "batch_size": BATCH_SIZE,
        "preprocessing": {
            "normalize": True,  # Normalize pixel values
            "contrast_enhancement": 1.5,  # Contrast enhancement factor
            "grayscale": False,  # Convert to grayscale
            "resize_method": "bilinear",  # Resize interpolation method
        }
    },
    "handwritten": {
        "name": "handwritten_text_recognition",
        "description": "Model for recognizing handwritten text in documents",
        "architecture": "CNN-BiLSTM-Attention",  # CNN with bidirectional LSTM and attention mechanism
        "input_shape": (INPUT_HEIGHT, INPUT_WIDTH, INPUT_CHANNELS),
        "backbone": "efficientnetb3",  # Feature extraction backbone
        "lstm_units": 512,  # Number of LSTM units
        "lstm_layers": 3,  # Number of LSTM layers
        "attention_units": 256,  # Number of attention units
        "dropout_rate": 0.3,  # Dropout rate for regularization
        "learning_rate": 0.0005,  # Initial learning rate
        "optimizer": "adam",  # Optimizer algorithm
        "confidence_threshold": CONFIDENCE_THRESHOLD * 0.9,  # Slightly lower threshold for handwritten text
        "verification_threshold": VERIFICATION_THRESHOLD * 0.9,  # Slightly lower threshold for handwritten text
        "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD * 0.9,  # Slightly lower threshold for handwritten text
        "max_text_length": MAX_TEXT_LENGTH,
        "beam_width": BEAM_WIDTH,
        "batch_size": BATCH_SIZE,
        "preprocessing": {
            "normalize": True,  # Normalize pixel values
            "contrast_enhancement": 1.2,  # Contrast enhancement factor
            "brightness_adjustment": 0.1,  # Brightness adjustment
            "grayscale": False,  # Convert to grayscale
            "resize_method": "bilinear",  # Resize interpolation method
        }
    },
    "hybrid": {
        "name": "hybrid_text_recognition",
        "description": "Model for recognizing both typed and handwritten text in documents",
        "architecture": "CNN-Transformer",  # CNN with transformer architecture
        "input_shape": (INPUT_HEIGHT, INPUT_WIDTH, INPUT_CHANNELS),
        "backbone": "efficientnetb4",  # Feature extraction backbone
        "transformer_layers": 6,  # Number of transformer layers
        "transformer_heads": 8,  # Number of attention heads
        "transformer_dim": 512,  # Transformer dimension
        "dropout_rate": 0.3,  # Dropout rate for regularization
        "learning_rate": 0.0003,  # Initial learning rate
        "optimizer": "adamw",  # Optimizer algorithm
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "verification_threshold": VERIFICATION_THRESHOLD,
        "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
        "max_text_length": MAX_TEXT_LENGTH,
        "beam_width": BEAM_WIDTH,
        "batch_size": BATCH_SIZE,
        "preprocessing": {
            "normalize": True,  # Normalize pixel values
            "contrast_enhancement": 1.3,  # Contrast enhancement factor
            "grayscale": False,  # Convert to grayscale
            "resize_method": "bilinear",  # Resize interpolation method
        }
    }
}

# Document type to model mapping
DOCUMENT_TYPE_MODEL_MAPPING = {
    "APPLICATION_FORM": "hybrid",  # Application forms often contain both typed and handwritten text
    "TAX_RETURN": "typed",  # Tax returns are typically typed/printed
    "BANK_STATEMENT": "typed",  # Bank statements are typically typed/printed
    "INVOICE": "typed",  # Invoices are typically typed/printed
    "ID_DOCUMENT": "hybrid",  # ID documents often contain both typed and handwritten elements
    "HANDWRITTEN_NOTE": "handwritten",  # Handwritten notes
    "BUSINESS_LICENSE": "typed",  # Business licenses are typically typed/printed
    "UTILITY_BILL": "typed",  # Utility bills are typically typed/printed
    "FINANCIAL_STATEMENT": "typed",  # Financial statements are typically typed/printed
    "CONTRACT": "hybrid",  # Contracts often contain both typed text and handwritten signatures
    "DEFAULT": "hybrid"  # Default to hybrid model for unknown document types
}

# Field type to model mapping for specialized field extraction
FIELD_TYPE_MODEL_MAPPING = {
    "SIGNATURE": "handwritten",  # Signatures are handwritten
    "CHECKBOX": "typed",  # Checkboxes are typically part of typed forms
    "DATE": "hybrid",  # Dates can be either typed or handwritten
    "AMOUNT": "hybrid",  # Amounts can be either typed or handwritten
    "ACCOUNT_NUMBER": "typed",  # Account numbers are typically typed
    "NAME": "hybrid",  # Names can be either typed or handwritten
    "ADDRESS": "hybrid",  # Addresses can be either typed or handwritten
    "DEFAULT": "hybrid"  # Default to hybrid model for unknown field types
}

# GPU optimization settings
GPU_OPTIMIZATION_SETTINGS = {
    "memory_growth": GPU_ALLOW_GROWTH,  # Allow memory growth to avoid allocating all GPU memory at once
    "memory_limit_mb": GPU_MEMORY_LIMIT,  # Memory limit in MB (8GB as specified in section 3.2.3)
    "mixed_precision": MIXED_PRECISION,  # Use mixed precision (FP16) for faster computation
    "xla_compilation": True,  # Use XLA (Accelerated Linear Algebra) compilation for faster execution
    "inter_op_parallelism": INTER_OP_PARALLELISM_THREADS,  # Number of threads for parallel operations
    "intra_op_parallelism": INTRA_OP_PARALLELISM_THREADS,  # Number of threads for operations that can be parallelized
    "gpu_per_process_memory_fraction": 0.9,  # Fraction of GPU memory to allocate per process
    "allow_soft_placement": True,  # Allow TensorFlow to place operations on CPU if GPU is not available
    "log_device_placement": False,  # Log device placement (for debugging)
    "jit_compilation": True,  # Use just-in-time compilation for faster execution
}

# Model versioning settings
MODEL_VERSIONING_SETTINGS = {
    "version_file": "version.json",  # File containing model version information
    "min_tf_version": TENSORFLOW_VERSION,  # Minimum TensorFlow version required
    "check_compatibility": True,  # Check model compatibility with current TensorFlow version
    "version_format": "semver",  # Semantic versioning format (major.minor.patch)
    "metadata_fields": [  # Metadata fields to include in version file
        "model_type",
        "architecture",
        "input_shape",
        "output_shape",
        "training_dataset",
        "accuracy",
        "created_at",
        "author",
    ],
}

# Performance monitoring settings
PERFORMANCE_MONITORING_SETTINGS = {
    "log_inference_time": True,  # Log inference time for performance monitoring
    "log_preprocessing_time": True,  # Log preprocessing time
    "log_postprocessing_time": True,  # Log postprocessing time
    "log_total_time": True,  # Log total processing time
    "log_gpu_utilization": True,  # Log GPU utilization
    "log_memory_usage": True,  # Log memory usage
    "performance_threshold_ms": 5000,  # Threshold for performance warnings (5 seconds)
    "batch_size_optimization": True,  # Automatically optimize batch size based on available GPU memory
    "cleanup_gpu_memory": True,  # Clean up GPU memory after inference to prevent memory leaks
}


def get_tensorflow_config() -> TensorFlowConfig:
    """
    Get the TensorFlow configuration for OCR processing.
    
    This function creates a TensorFlowConfig instance with the settings defined in this module.
    It provides a convenient way to access all TensorFlow configuration settings from a single point.
    
    Returns:
        TensorFlowConfig: Configuration instance with TensorFlow settings
    """
    return TensorFlowConfig(
        tensorflow_version=TENSORFLOW_VERSION,
        model_base_path=MODEL_BASE_PATH,
        typed_model_path=TYPED_MODEL_PATH,
        handwritten_model_path=HANDWRITTEN_MODEL_PATH,
        hybrid_model_path=HYBRID_MODEL_PATH,
        use_gpu=USE_GPU,
        gpu_memory_limit=GPU_MEMORY_LIMIT,
        gpu_allow_growth=GPU_ALLOW_GROWTH,
        mixed_precision=MIXED_PRECISION,
        inter_op_parallelism_threads=INTER_OP_PARALLELISM_THREADS,
        intra_op_parallelism_threads=INTRA_OP_PARALLELISM_THREADS,
        batch_size=BATCH_SIZE,
        confidence_threshold=CONFIDENCE_THRESHOLD,
        max_text_length=MAX_TEXT_LENGTH,
        beam_width=BEAM_WIDTH,
        input_shape=(INPUT_HEIGHT, INPUT_WIDTH, INPUT_CHANNELS),
        normalize_input=NORMALIZE_INPUT,
    )


def get_model_config(model_type: str) -> Dict[str, Any]:
    """
    Get the configuration for a specific model type.
    
    Args:
        model_type: Type of model (typed, handwritten, hybrid)
    
    Returns:
        Dictionary containing model configuration
        
    Raises:
        ValueError: If model_type is not supported
    """
    if model_type not in MODEL_ARCHITECTURES:
        raise ValueError(f"Unsupported model type: {model_type}. Supported types: {list(MODEL_ARCHITECTURES.keys())}")
    
    return MODEL_ARCHITECTURES[model_type]


def get_model_path(model_type: str) -> str:
    """
    Get the path for a specific model type.
    
    Args:
        model_type: Type of model (typed, handwritten, hybrid)
    
    Returns:
        Path to the model directory
        
    Raises:
        ValueError: If model_type is not supported
    """
    if model_type == "typed":
        return TYPED_MODEL_PATH
    elif model_type == "handwritten":
        return HANDWRITTEN_MODEL_PATH
    elif model_type == "hybrid":
        return HYBRID_MODEL_PATH
    else:
        raise ValueError(f"Unsupported model type: {model_type}. Supported types: typed, handwritten, hybrid")


def get_model_type_for_document(document_type: str) -> str:
    """
    Get the appropriate model type for a specific document type.
    
    Args:
        document_type: Type of document (APPLICATION_FORM, TAX_RETURN, etc.)
    
    Returns:
        Model type (typed, handwritten, hybrid)
    """
    return DOCUMENT_TYPE_MODEL_MAPPING.get(document_type, DOCUMENT_TYPE_MODEL_MAPPING["DEFAULT"])


def get_model_type_for_field(field_type: str) -> str:
    """
    Get the appropriate model type for a specific field type.
    
    Args:
        field_type: Type of field (SIGNATURE, CHECKBOX, DATE, etc.)
    
    Returns:
        Model type (typed, handwritten, hybrid)
    """
    return FIELD_TYPE_MODEL_MAPPING.get(field_type, FIELD_TYPE_MODEL_MAPPING["DEFAULT"])


def get_gpu_optimization_settings() -> Dict[str, Any]:
    """
    Get the GPU optimization settings for TensorFlow.
    
    Returns:
        Dictionary containing GPU optimization settings
    """
    return GPU_OPTIMIZATION_SETTINGS


def get_model_versioning_settings() -> Dict[str, Any]:
    """
    Get the model versioning settings.
    
    Returns:
        Dictionary containing model versioning settings
    """
    return MODEL_VERSIONING_SETTINGS


def get_performance_monitoring_settings() -> Dict[str, Any]:
    """
    Get the performance monitoring settings.
    
    Returns:
        Dictionary containing performance monitoring settings
    """
    return PERFORMANCE_MONITORING_SETTINGS


def log_tensorflow_config() -> None:
    """
    Log the TensorFlow configuration for debugging and monitoring.
    
    This function logs the current TensorFlow configuration settings to help with
    debugging and monitoring the OCR service.
    """
    config = get_tensorflow_config()
    logger.info(f"TensorFlow Configuration:")
    logger.info(f"  TensorFlow Version: {config.tensorflow_version}")
    logger.info(f"  Model Base Path: {config.model_base_path}")
    logger.info(f"  Typed Model Path: {config.typed_model_path}")
    logger.info(f"  Handwritten Model Path: {config.handwritten_model_path}")
    logger.info(f"  Hybrid Model Path: {config.hybrid_model_path}")
    logger.info(f"  Use GPU: {config.use_gpu}")
    logger.info(f"  GPU Memory Limit: {config.gpu_memory_limit} MB")
    logger.info(f"  GPU Allow Growth: {config.gpu_allow_growth}")
    logger.info(f"  Mixed Precision: {config.mixed_precision}")
    logger.info(f"  Batch Size: {config.batch_size}")
    logger.info(f"  Confidence Threshold: {config.confidence_threshold}")
    logger.info(f"  Input Shape: {config.input_shape}")


# Log configuration on module import for debugging
if os.environ.get("OCR_LOG_CONFIG", "false").lower() == "true":
    log_tensorflow_config()