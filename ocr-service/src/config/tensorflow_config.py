# -*- coding: utf-8 -*-
"""
TensorFlow Configuration Module for OCR Service

This module defines configuration parameters for TensorFlow models used in OCR processing.
It specifies model architectures, hyperparameters, GPU acceleration settings, confidence
thresholds, and model paths to ensure consistent model behavior across environments and
enable accurate text extraction from documents.
"""

import os
import logging
from typing import Dict, List, Optional, Union, Any

# Configure logger
logger = logging.getLogger(__name__)

# TensorFlow version requirement
TF_VERSION_REQUIRED = "2.15.0"

# GPU Configuration
GPU_CONFIG = {
    # Enable GPU acceleration
    "enable_gpu": True,
    # Allow memory growth (prevents TensorFlow from allocating all GPU memory at once)
    "allow_memory_growth": True,
    # Memory limit per GPU in MB (None means use all available memory)
    "memory_limit_mb": None,
    # Minimum required VRAM in GB
    "min_vram_gb": 8,
    # CUDA visible devices (None means use all available GPUs)
    "visible_devices": None,
    # Use mixed precision for faster computation with minimal accuracy loss
    "mixed_precision": True,
    # XLA compilation for improved performance
    "enable_xla": True,
    # GPU memory fraction to use (0.0 to 1.0)
    "per_process_gpu_memory_fraction": 0.9,
}

# Model Paths Configuration
MODEL_PATHS = {
    # Base directory for all models
    "base_dir": os.environ.get("OCR_MODELS_DIR", "/opt/ocr-service/models"),
    
    # Typed text recognition model
    "typed_text": {
        "path": "typed_text/v1.2.0",
        "weights": "typed_text_weights.h5",
        "config": "typed_text_config.json",
        "labels": "typed_text_labels.txt",
    },
    
    # Handwritten text recognition model
    "handwritten_text": {
        "path": "handwritten_text/v1.1.5",
        "weights": "handwritten_text_weights.h5",
        "config": "handwritten_text_config.json",
        "labels": "handwritten_text_labels.txt",
    },
    
    # Hybrid text recognition model (for mixed typed/handwritten documents)
    "hybrid_recognition": {
        "path": "hybrid_recognition/v1.0.3",
        "weights": "hybrid_recognition_weights.h5",
        "config": "hybrid_recognition_config.json",
        "labels": "hybrid_recognition_labels.txt",
    },
    
    # Document structure recognition model
    "structure_recognition": {
        "path": "structure_recognition/v1.2.1",
        "weights": "structure_recognition_weights.h5",
        "config": "structure_recognition_config.json",
        "labels": "structure_recognition_labels.txt",
    },
}

# Model Hyperparameters
MODEL_HYPERPARAMS = {
    # Typed text recognition model hyperparameters
    "typed_text": {
        "input_shape": (128, 1024, 1),  # Height, width, channels
        "batch_size": 32,
        "learning_rate": 0.001,
        "optimizer": "adam",
        "activation": "relu",
        "dropout_rate": 0.2,
        "l2_regularization": 0.0001,
        "use_batch_norm": True,
    },
    
    # Handwritten text recognition model hyperparameters
    "handwritten_text": {
        "input_shape": (64, 800, 1),  # Height, width, channels
        "batch_size": 16,
        "learning_rate": 0.0005,
        "optimizer": "adam",
        "activation": "relu",
        "dropout_rate": 0.3,
        "l2_regularization": 0.0002,
        "use_batch_norm": True,
        "bidirectional_lstm": True,
        "lstm_units": 256,
    },
    
    # Hybrid text recognition model hyperparameters
    "hybrid_recognition": {
        "input_shape": (96, 1024, 1),  # Height, width, channels
        "batch_size": 24,
        "learning_rate": 0.0008,
        "optimizer": "adam",
        "activation": "relu",
        "dropout_rate": 0.25,
        "l2_regularization": 0.00015,
        "use_batch_norm": True,
        "bidirectional_lstm": True,
        "lstm_units": 192,
    },
    
    # Document structure recognition model hyperparameters
    "structure_recognition": {
        "input_shape": (1024, 1024, 3),  # Height, width, channels
        "batch_size": 8,
        "learning_rate": 0.0003,
        "optimizer": "adam",
        "backbone": "resnet50",
        "feature_pyramid_levels": [3, 4, 5, 6, 7],
        "anchor_scales": [32, 64, 128, 256, 512],
        "anchor_ratios": [0.5, 1, 2],
        "rpn_nms_threshold": 0.7,
        "detection_nms_threshold": 0.3,
        "detection_min_confidence": 0.7,
    },
}

# Confidence Thresholds for Extraction
CONFIDENCE_THRESHOLDS = {
    # Minimum confidence score to accept an extracted field (0.0 to 1.0)
    "global_min_confidence": 0.75,
    
    # Field-specific confidence thresholds
    "fields": {
        # Business information fields
        "legal_name": 0.85,
        "dba_name": 0.80,
        "ein": 0.95,  # Tax ID requires high confidence
        "address": 0.80,
        "city": 0.85,
        "state": 0.90,
        "zip_code": 0.90,
        "phone": 0.90,
        "email": 0.85,
        "website": 0.80,
        
        # Financial information fields
        "monthly_revenue": 0.90,
        "annual_revenue": 0.90,
        "requested_amount": 0.95,
        "bank_account": 0.98,  # Banking info requires very high confidence
        "routing_number": 0.98,  # Banking info requires very high confidence
        
        # Owner information fields
        "owner_name": 0.85,
        "owner_ssn": 0.98,  # SSN requires very high confidence
        "owner_dob": 0.90,
        "owner_address": 0.80,
        "owner_city": 0.85,
        "owner_state": 0.90,
        "owner_zip_code": 0.90,
        
        # Default for any unlisted fields
        "default": 0.80,
    },
    
    # Document type specific thresholds
    "document_types": {
        "application_form": 0.80,
        "bank_statement": 0.85,
        "tax_return": 0.90,
        "id_document": 0.95,
        "utility_bill": 0.80,
        "default": 0.80,
    },
}

# Model Architecture Configurations
MODEL_ARCHITECTURES = {
    # Typed text recognition model architecture
    "typed_text": {
        "type": "cnn_lstm_ctc",
        "cnn_layers": 5,
        "cnn_filters": [64, 128, 256, 256, 512],
        "cnn_kernel_sizes": [(3, 3), (3, 3), (3, 3), (3, 3), (3, 3)],
        "cnn_pool_sizes": [(2, 2), (2, 2), (2, 1), (2, 1), (2, 1)],
        "lstm_layers": 2,
        "lstm_units": 256,
        "bidirectional": True,
    },
    
    # Handwritten text recognition model architecture
    "handwritten_text": {
        "type": "cnn_lstm_attention",
        "cnn_layers": 6,
        "cnn_filters": [64, 128, 256, 256, 512, 512],
        "cnn_kernel_sizes": [(3, 3), (3, 3), (3, 3), (3, 3), (3, 3), (3, 3)],
        "cnn_pool_sizes": [(2, 2), (2, 2), (2, 1), (2, 1), (2, 1), (1, 1)],
        "lstm_layers": 3,
        "lstm_units": 256,
        "attention_dim": 128,
        "bidirectional": True,
    },
    
    # Hybrid text recognition model architecture
    "hybrid_recognition": {
        "type": "cnn_transformer",
        "cnn_layers": 5,
        "cnn_filters": [64, 128, 256, 256, 512],
        "cnn_kernel_sizes": [(3, 3), (3, 3), (3, 3), (3, 3), (3, 3)],
        "cnn_pool_sizes": [(2, 2), (2, 2), (2, 1), (2, 1), (2, 1)],
        "transformer_layers": 4,
        "transformer_heads": 8,
        "transformer_dim": 512,
        "transformer_ff_dim": 2048,
    },
    
    # Document structure recognition model architecture
    "structure_recognition": {
        "type": "mask_rcnn",
        "backbone": "resnet50",
        "fpn_layers": ["P2", "P3", "P4", "P5", "P6"],
        "roi_pool_size": (7, 7),
        "mask_pool_size": (14, 14),
        "mask_shape": (28, 28),
        "rpn_anchor_scales": (32, 64, 128, 256, 512),
        "rpn_anchor_ratios": [0.5, 1, 2],
        "rpn_nms_threshold": 0.7,
        "rpn_train_anchors_per_image": 256,
        "post_nms_rois_training": 2000,
        "post_nms_rois_inference": 1000,
        "use_mini_mask": True,
        "mini_mask_shape": (56, 56),
    },
}

# TensorFlow Optimization Settings
TF_OPTIMIZATION = {
    # Enable XLA (Accelerated Linear Algebra) compilation
    "enable_xla": True,
    # Enable mixed precision training (float16/float32)
    "mixed_precision": True,
    # Parallel processing settings
    "inter_op_parallelism_threads": 0,  # 0 means auto-select based on CPU cores
    "intra_op_parallelism_threads": 0,  # 0 means auto-select based on CPU cores
    # TensorFlow memory optimization
    "enable_tensor_fusion": True,
    "tensor_fusion_threshold": 64,  # in MB
    # Kernel optimization
    "jit_level": 1,  # 0=disabled, 1=on-demand, 2=always
    # Graph optimization level
    "optimization_level": 3,  # 0=L0, 1=L1, 2=L2, 3=L3 (most aggressive)
}

# TensorFlow Session Configuration
def get_session_config() -> Dict[str, Any]:
    """
    Returns the TensorFlow session configuration dictionary based on the defined settings.
    
    Returns:
        Dict[str, Any]: TensorFlow session configuration dictionary
    """
    return {
        "allow_soft_placement": True,
        "log_device_placement": False,
        "gpu_options": {
            "allow_growth": GPU_CONFIG["allow_memory_growth"],
            "per_process_gpu_memory_fraction": GPU_CONFIG["per_process_gpu_memory_fraction"] 
                if not GPU_CONFIG["allow_memory_growth"] else None,
        },
        "device_count": {"GPU": 0} if not GPU_CONFIG["enable_gpu"] else None,
        "inter_op_parallelism_threads": TF_OPTIMIZATION["inter_op_parallelism_threads"],
        "intra_op_parallelism_threads": TF_OPTIMIZATION["intra_op_parallelism_threads"],
        "use_per_session_threads": True,
        "graph_options": {
            "optimizer_options": {
                "global_jit_level": TF_OPTIMIZATION["jit_level"],
                "opt_level": TF_OPTIMIZATION["optimization_level"],
            }
        },
    }

# Function to get model configuration by type
def get_model_config(model_type: str) -> Dict[str, Any]:
    """
    Returns the complete configuration for a specific model type.
    
    Args:
        model_type (str): Type of model (typed_text, handwritten_text, hybrid_recognition, structure_recognition)
    
    Returns:
        Dict[str, Any]: Complete model configuration including paths, hyperparameters, and architecture
    
    Raises:
        ValueError: If the model type is not supported
    """
    if model_type not in MODEL_PATHS:
        raise ValueError(f"Unsupported model type: {model_type}. Supported types: {list(MODEL_PATHS.keys())}")
    
    # Construct full model paths
    base_dir = MODEL_PATHS["base_dir"]
    model_path_config = MODEL_PATHS[model_type]
    full_model_path = os.path.join(base_dir, model_path_config["path"])
    
    # Combine all configuration elements
    return {
        "paths": {
            "model_dir": full_model_path,
            "weights_path": os.path.join(full_model_path, model_path_config["weights"]),
            "config_path": os.path.join(full_model_path, model_path_config["config"]),
            "labels_path": os.path.join(full_model_path, model_path_config["labels"]),
        },
        "hyperparameters": MODEL_HYPERPARAMS[model_type],
        "architecture": MODEL_ARCHITECTURES[model_type],
    }

# Function to get confidence threshold for a specific field and document type
def get_confidence_threshold(field_name: str, document_type: Optional[str] = None) -> float:
    """
    Returns the confidence threshold for a specific field and document type.
    
    Args:
        field_name (str): Name of the field
        document_type (Optional[str]): Type of document (default: None)
    
    Returns:
        float: Confidence threshold value (0.0 to 1.0)
    """
    # Get field-specific threshold or default
    field_threshold = CONFIDENCE_THRESHOLDS["fields"].get(
        field_name, CONFIDENCE_THRESHOLDS["fields"]["default"]
    )
    
    # Get document-type-specific threshold or default
    doc_threshold = CONFIDENCE_THRESHOLDS["global_min_confidence"]
    if document_type is not None:
        doc_threshold = CONFIDENCE_THRESHOLDS["document_types"].get(
            document_type, CONFIDENCE_THRESHOLDS["document_types"]["default"]
        )
    
    # Return the higher of the two thresholds
    return max(field_threshold, doc_threshold)

# Function to initialize TensorFlow with the proper GPU settings
def initialize_tensorflow() -> None:
    """
    Initializes TensorFlow with the proper GPU settings.
    This function should be called before any TensorFlow operations.
    
    Raises:
        ImportError: If TensorFlow is not installed or version requirements are not met
        RuntimeError: If GPU requirements are not met
    """
    try:
        import tensorflow as tf
        from tensorflow.python.client import device_lib
        
        # Check TensorFlow version
        tf_version = tf.__version__
        if tf_version != TF_VERSION_REQUIRED:
            logger.warning(
                f"TensorFlow version mismatch. Required: {TF_VERSION_REQUIRED}, Found: {tf_version}. "
                f"This may cause compatibility issues."
            )
        
        # Configure GPU memory growth to prevent TensorFlow from allocating all memory at once
        if GPU_CONFIG["enable_gpu"]:
            gpus = tf.config.experimental.list_physical_devices('GPU')
            if not gpus:
                logger.warning("No GPU found. Falling back to CPU.")
            else:
                logger.info(f"Found {len(gpus)} GPU(s): {gpus}")
                
                # Set visible devices if specified
                if GPU_CONFIG["visible_devices"] is not None:
                    visible_gpus = [gpus[i] for i in GPU_CONFIG["visible_devices"] if i < len(gpus)]
                    tf.config.experimental.set_visible_devices(visible_gpus, 'GPU')
                    logger.info(f"Using GPUs: {visible_gpus}")
                
                # Configure each GPU
                for gpu in gpus:
                    try:
                        if GPU_CONFIG["allow_memory_growth"]:
                            tf.config.experimental.set_memory_growth(gpu, True)
                            logger.info(f"Enabled memory growth for {gpu}")
                        
                        # Set memory limit if specified
                        if GPU_CONFIG["memory_limit_mb"] is not None:
                            tf.config.experimental.set_virtual_device_configuration(
                                gpu,
                                [tf.config.experimental.VirtualDeviceConfiguration(
                                    memory_limit=GPU_CONFIG["memory_limit_mb"]
                                )]
                            )
                            logger.info(f"Set memory limit to {GPU_CONFIG['memory_limit_mb']}MB for {gpu}")
                    except RuntimeError as e:
                        logger.error(f"Error configuring GPU {gpu}: {str(e)}")
                
                # Check GPU memory requirements
                gpu_devices = device_lib.list_local_devices()
                for device in gpu_devices:
                    if device.device_type == "GPU":
                        gpu_memory = device.memory_limit / (1024 ** 3)  # Convert to GB
                        if gpu_memory < GPU_CONFIG["min_vram_gb"]:
                            logger.warning(
                                f"GPU {device.name} has {gpu_memory:.2f}GB VRAM, which is less than the "
                                f"required {GPU_CONFIG['min_vram_gb']}GB. This may affect performance."
                            )
        
        # Enable mixed precision if requested
        if GPU_CONFIG["mixed_precision"] and GPU_CONFIG["enable_gpu"]:
            policy = tf.keras.mixed_precision.Policy('mixed_float16')
            tf.keras.mixed_precision.set_global_policy(policy)
            logger.info("Enabled mixed precision training (float16/float32)")
        
        # Enable XLA compilation if requested
        if TF_OPTIMIZATION["enable_xla"]:
            tf.config.optimizer.set_jit(True)
            logger.info("Enabled XLA compilation")
        
        logger.info("TensorFlow initialized successfully with GPU support")
        
    except ImportError as e:
        logger.error(f"Failed to import TensorFlow: {str(e)}")
        raise ImportError("TensorFlow is not installed or cannot be imported. Please install TensorFlow 2.15.0.")
    except Exception as e:
        logger.error(f"Error initializing TensorFlow: {str(e)}")
        raise RuntimeError(f"Failed to initialize TensorFlow: {str(e)}")