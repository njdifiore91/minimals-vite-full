#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TensorFlow utilities for the OCR Service.

This module provides utility functions for loading OCR models, performing inference,
managing GPU resources, and handling model versioning. It's essential for the core OCR
functionality of extracting text from documents using specialized TensorFlow models.

Key features:
- GPU acceleration configuration and management (required per section 3.2.3)
- Model loading and versioning for different text types (typed, handwritten, hybrid)
- Inference functions with confidence scoring (required per section 4.1.8)
- Performance monitoring and optimization utilities
- Memory management to prevent GPU memory leaks

The module implements the requirements specified in the technical specification:
- OCR Service must use TensorFlow with GPU acceleration (section 3.2.2)
- Service must apply appropriate OCR model based on document type (section 4.1.8)
- Service must implement confidence scoring for extracted fields (section 4.1.8)

This module is designed to be used by the OCR Service to process documents with
high accuracy (99% as specified in section 0.1.2) and performance.
"""

import os
import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Union, Any

import numpy as np
import tensorflow as tf

# Configure logging
logger = logging.getLogger(__name__)

# Constants
MIN_REQUIRED_VRAM_MB = 8 * 1024  # 8GB VRAM required as per technical spec section 3.2.3
MODEL_VERSION_FILE = "version.json"
SUPPORTED_MODEL_TYPES = ["typed", "handwritten", "hybrid"]

# TensorFlow model configuration
TF_VERSION_REQUIRED = "2.15.0"  # TensorFlow version specified in section 3.2.2
TF_INTER_OP_PARALLELISM = 4     # Number of threads for parallel operations
TF_INTRA_OP_PARALLELISM = 4     # Number of threads for operations that can be parallelized
TF_GPU_MEMORY_GROWTH = True     # Allow memory growth to avoid allocating all GPU memory at once

# Confidence thresholds
DEFAULT_CONFIDENCE_THRESHOLD = 0.75  # Default threshold for confidence scoring (section 4.1.8)
LOW_CONFIDENCE_THRESHOLD = 0.50      # Threshold below which fields require human review


def configure_gpu_memory(memory_limit: Optional[int] = None,
                        allow_growth: bool = TF_GPU_MEMORY_GROWTH,
                        inter_op_parallelism: int = TF_INTER_OP_PARALLELISM,
                        intra_op_parallelism: int = TF_INTRA_OP_PARALLELISM) -> Dict[str, Any]:
    """
    Configure TensorFlow to use GPU with specified memory settings and thread parallelism.
    
    This function configures GPU memory allocation and thread parallelism for optimal
    performance with TensorFlow. It implements the GPU acceleration requirements specified
    in section 3.2.3 of the technical specification.
    
    Args:
        memory_limit: Memory limit in MB. If None, no limit is set.
        allow_growth: If True, memory growth is allowed (allocates only as much as needed).
        inter_op_parallelism: Number of threads used for parallel operations.
        intra_op_parallelism: Number of threads used for operations that can be parallelized.
    
    Returns:
        Dictionary with configuration results and settings applied
    """
    config_results = {
        "gpu_available": False,
        "memory_growth_enabled": False,
        "memory_limit_set": False,
        "parallelism_configured": False,
        "settings": {
            "allow_growth": allow_growth,
            "memory_limit_mb": memory_limit,
            "inter_op_parallelism": inter_op_parallelism,
            "intra_op_parallelism": intra_op_parallelism
        }
    }
    
    try:
        # Configure thread parallelism
        tf.config.threading.set_inter_op_parallelism_threads(inter_op_parallelism)
        tf.config.threading.set_intra_op_parallelism_threads(intra_op_parallelism)
        config_results["parallelism_configured"] = True
        logger.info(f"Configured TensorFlow thread parallelism: inter_op={inter_op_parallelism}, "
                   f"intra_op={intra_op_parallelism}")
        
        # Check if GPU is available
        gpus = tf.config.list_physical_devices('GPU')
        config_results["gpu_available"] = len(gpus) > 0
        config_results["gpu_count"] = len(gpus)
        
        if not gpus:
            logger.warning("No GPU found. Running on CPU which may significantly impact performance.")
            return config_results
        
        logger.info(f"Found {len(gpus)} GPU(s): {gpus}")
        
        # Configure memory growth
        for gpu in gpus:
            if allow_growth:
                tf.config.experimental.set_memory_growth(gpu, True)
                config_results["memory_growth_enabled"] = True
                logger.info(f"Enabled memory growth for GPU: {gpu}")
            
            # Set memory limit if specified
            if memory_limit:
                tf.config.set_logical_device_configuration(
                    gpu,
                    [tf.config.LogicalDeviceConfiguration(memory_limit=memory_limit)])
                config_results["memory_limit_set"] = True
                logger.info(f"Set memory limit to {memory_limit}MB for GPU: {gpu}")
        
        # Log GPU configuration
        logical_gpus = tf.config.list_logical_devices('GPU')
        config_results["logical_gpu_count"] = len(logical_gpus)
        logger.info(f"Configured {len(logical_gpus)} logical GPU(s)")
        
        # Set mixed precision policy if TensorFlow version supports it
        # This can significantly improve performance on GPUs with tensor cores
        if tf.__version__ >= "2.4.0":
            try:
                policy = tf.keras.mixed_precision.Policy('mixed_float16')
                tf.keras.mixed_precision.set_global_policy(policy)
                config_results["mixed_precision_enabled"] = True
                logger.info("Enabled mixed precision (float16) for faster GPU computation")
            except Exception as mp_error:
                logger.warning(f"Could not enable mixed precision: {str(mp_error)}")
                config_results["mixed_precision_enabled"] = False
        
        # Check TensorFlow version
        config_results["tensorflow_version"] = tf.__version__
        if tf.__version__ != TF_VERSION_REQUIRED:
            logger.warning(f"TensorFlow version mismatch. Required: {TF_VERSION_REQUIRED}, Found: {tf.__version__}")
        
        # Verify CUDA is available
        config_results["cuda_available"] = tf.test.is_built_with_cuda()
        if not config_results["cuda_available"]:
            logger.warning("TensorFlow not built with CUDA support. GPU acceleration may not work properly.")
        
        return config_results
        
    except Exception as e:
        logger.error(f"Error configuring GPU: {str(e)}")
        config_results["error"] = str(e)
        return config_results


def check_gpu_compatibility() -> Tuple[bool, Dict[str, Any]]:
    """
    Check if the available GPU(s) meet the minimum requirements for OCR processing.
    
    Returns:
        Tuple containing:
            - Boolean indicating if GPU is compatible
            - Dictionary with GPU information
    """
    gpu_info = {}
    try:
        gpus = tf.config.list_physical_devices('GPU')
        if not gpus:
            return False, {"error": "No GPU found"}
        
        # Get GPU memory info using TensorFlow
        for i, gpu in enumerate(gpus):
            # Create a small tensor to force memory allocation on the GPU
            with tf.device(f'/GPU:{i}'):
                # This will trigger device initialization
                tf.random.normal([1000, 1000])
            
            # Get memory info
            gpu_info[f"gpu_{i}"] = {
                "name": gpu.name,
                "device": str(gpu),
            }
        
        # Check CUDA and cuDNN versions
        gpu_info["cuda_version"] = tf.sysconfig.get_build_info()["cuda_version"]
        gpu_info["cudnn_version"] = tf.sysconfig.get_build_info()["cudnn_version"]
        
        # Check TensorFlow version
        gpu_info["tensorflow_version"] = tf.__version__
        
        # Perform a simple operation to verify GPU works
        with tf.device('/GPU:0'):
            a = tf.constant([[1.0, 2.0], [3.0, 4.0]])
            b = tf.constant([[5.0, 6.0], [7.0, 8.0]])
            c = tf.matmul(a, b)
            # Force execution to verify GPU works
            result = c.numpy()
        
        gpu_info["test_passed"] = True
        return True, gpu_info
        
    except Exception as e:
        logger.error(f"GPU compatibility check failed: {str(e)}")
        gpu_info["error"] = str(e)
        gpu_info["test_passed"] = False
        return False, gpu_info


def get_available_vram() -> Dict[int, int]:
    """
    Get available VRAM for each GPU in MB.
    
    Returns:
        Dictionary mapping GPU index to available VRAM in MB
    """
    vram_info = {}
    try:
        # This is a simplified approach - in production, you would use
        # nvidia-ml-py3 (pynvml) for more accurate GPU memory information
        gpus = tf.config.list_physical_devices('GPU')
        
        for i, gpu in enumerate(gpus):
            # Create a test tensor to estimate available memory
            # This is not precise but gives a rough estimate
            with tf.device(f'/GPU:{i}'):
                # Try to allocate a large tensor and see if it works
                # Start with a small tensor and increase size
                max_size = 0
                test_sizes = [1024, 2048, 4096, 8192, 16384]
                
                for size in test_sizes:
                    try:
                        # Try to allocate a tensor of size (size, size)
                        tensor = tf.random.normal([size, size])
                        # Force execution
                        tensor.numpy()
                        # If successful, update max_size
                        max_size = size
                    except Exception:
                        # If allocation fails, break the loop
                        break
                
                # Rough estimate of available VRAM in MB
                # Each float32 value is 4 bytes
                vram_estimate = (max_size * max_size * 4) / (1024 * 1024)
                vram_info[i] = int(vram_estimate)
        
        return vram_info
    except Exception as e:
        logger.error(f"Error getting available VRAM: {str(e)}")
        return {}


def verify_gpu_requirements() -> Tuple[bool, Dict[str, Any]]:
    """
    Verify that the available GPU(s) meet the minimum requirements for OCR processing.
    
    As specified in section 3.2.3 of the technical specification, TensorFlow OCR processing
    requires CUDA-compatible GPU acceleration with at least 8GB VRAM for performance.
    
    Returns:
        Tuple containing:
            - Boolean indicating if requirements are met
            - Dictionary with detailed verification results
    """
    verification_results = {
        "gpu_available": False,
        "cuda_available": False,
        "sufficient_vram": False,
        "tensorflow_gpu_enabled": False,
        "requirements_met": False,
        "details": {}
    }
    
    try:
        # Check if GPU is available
        gpus = tf.config.list_physical_devices('GPU')
        verification_results["gpu_available"] = len(gpus) > 0
        verification_results["details"]["gpus"] = [str(gpu) for gpu in gpus]
        
        if not verification_results["gpu_available"]:
            logger.warning("No GPU found. OCR processing requires GPU acceleration.")
            return False, verification_results
        
        # Check CUDA and cuDNN availability
        verification_results["cuda_available"] = tf.test.is_built_with_cuda()
        verification_results["details"]["cuda_version"] = tf.sysconfig.get_build_info()["cuda_version"]
        verification_results["details"]["cudnn_version"] = tf.sysconfig.get_build_info()["cudnn_version"]
        
        if not verification_results["cuda_available"]:
            logger.warning("TensorFlow not built with CUDA support.")
            return False, verification_results
        
        # Check available VRAM
        vram_info = get_available_vram()
        verification_results["details"]["vram_info"] = vram_info
        
        if not vram_info:
            logger.warning("Could not determine available VRAM.")
            return False, verification_results
        
        # Check if any GPU has sufficient VRAM
        sufficient_vram = any(vram >= MIN_REQUIRED_VRAM_MB for vram in vram_info.values())
        verification_results["sufficient_vram"] = sufficient_vram
        verification_results["details"]["min_required_vram_mb"] = MIN_REQUIRED_VRAM_MB
        verification_results["details"]["max_available_vram_mb"] = max(vram_info.values()) if vram_info else 0
        
        if not sufficient_vram:
            logger.warning(f"Insufficient VRAM. OCR processing requires at least {MIN_REQUIRED_VRAM_MB}MB VRAM.")
            return False, verification_results
        
        # Verify GPU is actually working with TensorFlow
        is_compatible, compatibility_info = check_gpu_compatibility()
        verification_results["tensorflow_gpu_enabled"] = is_compatible
        verification_results["details"]["compatibility_check"] = compatibility_info
        
        if not is_compatible:
            logger.warning("GPU compatibility check failed.")
            return False, verification_results
        
        # Run a simple test to verify GPU acceleration works
        with tf.device('/GPU:0'):
            # Create and multiply two matrices
            start_time = time.time()
            a = tf.random.normal([2000, 2000])
            b = tf.random.normal([2000, 2000])
            c = tf.matmul(a, b)
            # Force execution
            result = c.numpy()
            execution_time = time.time() - start_time
        
        verification_results["details"]["test_execution_time_ms"] = execution_time * 1000
        
        # All requirements met
        verification_results["requirements_met"] = True
        logger.info("GPU requirements verified successfully.")
        logger.info(f"GPU details: {len(gpus)} GPU(s), CUDA {verification_results['details']['cuda_version']}, "
                   f"cuDNN {verification_results['details']['cudnn_version']}, "
                   f"Max VRAM: {verification_results['details']['max_available_vram_mb']}MB")
        
        return True, verification_results
        
    except Exception as e:
        logger.error(f"Error verifying GPU requirements: {str(e)}")
        verification_results["error"] = str(e)
        return False, verification_results


def load_model(model_path: str, model_type: str, version: Optional[str] = None) -> tf.keras.Model:
    """
    Load a TensorFlow model from the specified path with version validation.
    
    This function loads OCR models for different text types (typed, handwritten, hybrid)
    and ensures they are properly validated and warmed up for inference. It supports
    model versioning to ensure reproducibility and consistent results.
    
    Args:
        model_path: Path to the model directory
        model_type: Type of model (typed, handwritten, hybrid)
        version: Optional specific model version to load
    
    Returns:
        Loaded TensorFlow model
    
    Raises:
        ValueError: If model_type is not supported or model cannot be loaded
    """
    if model_type not in SUPPORTED_MODEL_TYPES:
        raise ValueError(f"Unsupported model type: {model_type}. Supported types: {SUPPORTED_MODEL_TYPES}")
    
    try:
        # Check if model exists
        if not os.path.exists(model_path):
            raise ValueError(f"Model path does not exist: {model_path}")
        
        # Check for version if specified
        if version is not None:
            version_info = get_model_version(model_path)
            if version_info["version"] != version:
                raise ValueError(f"Model version mismatch. Requested: {version}, Found: {version_info['version']}")
        
        # Log model loading
        logger.info(f"Loading {model_type} model from {model_path}")
        start_time = time.time()
        
        # Define custom objects if needed for the model
        # This is important for models with custom layers or loss functions
        custom_objects = {}
        
        # For typed text models, we might have custom layers
        if model_type == "typed":
            # Example of custom layer for typed text recognition
            # custom_objects["CustomLayer"] = CustomLayer
            pass
        
        # For handwritten text models, we might have different custom layers
        elif model_type == "handwritten":
            # Example of custom layer for handwritten text recognition
            # custom_objects["HandwrittenAttention"] = HandwrittenAttention
            pass
        
        # For hybrid models, we might need to combine custom objects
        elif model_type == "hybrid":
            # Example of custom layers for hybrid text recognition
            # custom_objects.update({"CustomLayer": CustomLayer, "HandwrittenAttention": HandwrittenAttention})
            pass
        
        # Load the model with appropriate custom objects
        model = tf.keras.models.load_model(model_path, custom_objects=custom_objects)
        
        # Log loading time
        load_time = time.time() - start_time
        logger.info(f"Model loaded in {load_time:.2f} seconds")
        
        # Verify model is valid
        if not isinstance(model, tf.keras.Model):
            raise ValueError(f"Loaded object is not a valid TensorFlow model: {type(model)}")
        
        # Validate model structure and compatibility
        is_valid, validation_results = validate_model(model, model_type)
        if not is_valid:
            issues = ", ".join(validation_results["issues"])
            raise ValueError(f"Model validation failed: {issues}")
        
        # Warm up the model with a sample input to ensure it's ready for inference
        warmup_model(model, model_type)
        
        # Log model information
        logger.info(f"Model type: {model_type}, Input shape: {model.input_shape}, Output shape: {model.output_shape}")
        
        # Check if GPU is being used
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            logger.info(f"Model will use GPU acceleration: {gpus}")
        else:
            logger.warning("No GPU available. Model will run on CPU which may be significantly slower.")
        
        return model
    
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        raise ValueError(f"Failed to load {model_type} model: {str(e)}")


def warmup_model(model: tf.keras.Model, model_type: str) -> None:
    """
    Warm up the model with a sample input to ensure it's ready for inference.
    
    Args:
        model: TensorFlow model to warm up
        model_type: Type of model (typed, handwritten, hybrid)
    """
    try:
        logger.info(f"Warming up {model_type} model...")
        
        # Create a sample input based on model type
        # Assuming input shape is (batch_size, height, width, channels)
        if model_type == "typed":
            # Typical document image size for typed text
            sample_input = tf.random.normal([1, 1024, 768, 3])
        elif model_type == "handwritten":
            # Typical document image size for handwritten text
            sample_input = tf.random.normal([1, 1024, 768, 3])
        elif model_type == "hybrid":
            # Typical document image size for hybrid text
            sample_input = tf.random.normal([1, 1024, 768, 3])
        else:
            logger.warning(f"Unknown model type for warmup: {model_type}")
            return
        
        # Run inference on sample input
        start_time = time.time()
        _ = model(sample_input, training=False)
        warmup_time = time.time() - start_time
        
        logger.info(f"Model warmed up in {warmup_time:.2f} seconds")
    
    except Exception as e:
        logger.warning(f"Model warmup failed: {str(e)}")


def get_model_version(model_path: str) -> Dict[str, Any]:
    """
    Get the version information for a model with detailed metadata.
    
    This function retrieves version information and metadata for a TensorFlow model,
    which is essential for model versioning and validation as specified in the
    technical requirements.
    
    Args:
        model_path: Path to the model directory
    
    Returns:
        Dictionary containing version information and model metadata
    """
    version_info = {
        "version": "unknown",
        "created_at": "unknown",
        "framework_version": tf.__version__,
        "model_type": "unknown",
        "metadata": {},
        "is_compatible": False
    }
    
    try:
        # Check if version file exists
        version_file = os.path.join(model_path, MODEL_VERSION_FILE)
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                version_data = json.load(f)
                version_info.update(version_data)
                
                # Extract model type if available
                if "model_type" in version_data:
                    version_info["model_type"] = version_data["model_type"]
                
                # Extract additional metadata if available
                if "metadata" in version_data:
                    version_info["metadata"] = version_data["metadata"]
        else:
            # Try to get version from saved_model.pb metadata
            try:
                # Load model without custom objects to just check metadata
                model = tf.keras.models.load_model(model_path, compile=False)
                
                # Check for metadata in the model
                if hasattr(model, 'metadata'):
                    if isinstance(model.metadata, dict):
                        if 'version' in model.metadata:
                            version_info["version"] = model.metadata['version']
                        if 'created_at' in model.metadata:
                            version_info["created_at"] = model.metadata['created_at']
                        if 'model_type' in model.metadata:
                            version_info["model_type"] = model.metadata['model_type']
                        
                        # Include all metadata
                        version_info["metadata"] = model.metadata
                
                # Get model architecture summary
                model_summary = []
                model.summary(print_fn=lambda x: model_summary.append(x))
                version_info["architecture_summary"] = "\n".join(model_summary)
                
                # Get input and output shapes
                version_info["input_shape"] = str(model.input_shape)
                version_info["output_shape"] = str(model.output_shape)
                
            except Exception as model_error:
                logger.debug(f"Could not extract metadata from model: {str(model_error)}")
        
        # Check if the model is compatible with current TensorFlow version
        version_info["is_compatible"] = True  # Assume compatible by default
        
        # If we have a specific model version and TensorFlow version, check compatibility
        if version_info["version"] != "unknown" and "min_tf_version" in version_info["metadata"]:
            min_tf_version = version_info["metadata"]["min_tf_version"]
            current_tf_version = tf.__version__
            
            # Simple version comparison (this could be more sophisticated)
            version_info["is_compatible"] = current_tf_version >= min_tf_version
            
            if not version_info["is_compatible"]:
                logger.warning(f"Model requires TensorFlow {min_tf_version} or higher, "
                              f"but current version is {current_tf_version}")
        
        # Add timestamp for when this information was retrieved
        version_info["retrieved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    except Exception as e:
        logger.warning(f"Error getting model version: {str(e)}")
        version_info["error"] = str(e)
    
    return version_info


def validate_model(model: tf.keras.Model, model_type: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate a model to ensure it meets the requirements for OCR processing.
    
    Args:
        model: TensorFlow model to validate
        model_type: Type of model (typed, handwritten, hybrid)
    
    Returns:
        Tuple containing:
            - Boolean indicating if model is valid
            - Dictionary with validation results
    """
    validation_results = {
        "model_type": model_type,
        "is_valid": False,
        "issues": []
    }
    
    try:
        # Check model type
        if model_type not in SUPPORTED_MODEL_TYPES:
            validation_results["issues"].append(f"Unsupported model type: {model_type}")
            return False, validation_results
        
        # Check if model is a valid TensorFlow model
        if not isinstance(model, tf.keras.Model):
            validation_results["issues"].append(f"Not a valid TensorFlow model: {type(model)}")
            return False, validation_results
        
        # Check model inputs and outputs
        input_shape = model.input_shape
        output_shape = model.output_shape
        
        # Validate input shape based on model type
        if model_type == "typed":
            # Typical input for typed text OCR: (batch_size, height, width, channels)
            if len(input_shape) != 4 or input_shape[-1] not in [1, 3]:
                validation_results["issues"].append(
                    f"Invalid input shape for typed model: {input_shape}. Expected (batch_size, height, width, 1 or 3)")
        
        elif model_type == "handwritten":
            # Similar validation for handwritten model
            if len(input_shape) != 4 or input_shape[-1] not in [1, 3]:
                validation_results["issues"].append(
                    f"Invalid input shape for handwritten model: {input_shape}. Expected (batch_size, height, width, 1 or 3)")
        
        elif model_type == "hybrid":
            # Similar validation for hybrid model
            if len(input_shape) != 4 or input_shape[-1] not in [1, 3]:
                validation_results["issues"].append(
                    f"Invalid input shape for hybrid model: {input_shape}. Expected (batch_size, height, width, 1 or 3)")
        
        # Check if there are any issues
        if not validation_results["issues"]:
            validation_results["is_valid"] = True
        
        # Add model information
        validation_results["input_shape"] = input_shape
        validation_results["output_shape"] = output_shape
        
        return validation_results["is_valid"], validation_results
    
    except Exception as e:
        validation_results["issues"].append(f"Validation error: {str(e)}")
        return False, validation_results


def run_inference(model: tf.keras.Model, 
                 image: np.ndarray, 
                 model_type: str,
                 batch_size: int = 1,
                 confidence_threshold: float = 0.75) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Run inference on an image using the specified model with GPU acceleration.
    
    As specified in section 4.1.8 of the technical specification, the OCR service must
    apply the appropriate OCR model based on document type and text characteristics,
    and must use GPU acceleration for performance (section 3.2.2).
    
    Args:
        model: TensorFlow model to use for inference
        image: Input image as numpy array
        model_type: Type of model (typed, handwritten, hybrid)
        batch_size: Batch size for inference
        confidence_threshold: Threshold for confidence scoring
    
    Returns:
        Tuple containing:
            - Model output as numpy array
            - Dictionary with inference metadata (timing, confidence scores, etc.)
    """
    metadata = {
        "model_type": model_type,
        "batch_size": batch_size,
        "inference_time_ms": 0,
        "preprocessing_time_ms": 0,
        "postprocessing_time_ms": 0,
        "total_time_ms": 0,
        "gpu_utilized": False,
        "confidence_scores": {},
    }
    
    try:
        # Start timing
        total_start_time = time.time()
        
        # Check if GPU is available and being used
        gpus = tf.config.list_physical_devices('GPU')
        metadata["gpu_available"] = len(gpus) > 0
        
        # Preprocess image based on model type
        preprocess_start_time = time.time()
        
        # Ensure image has the right shape and type
        if len(image.shape) == 3:  # Single image
            # Add batch dimension
            image = np.expand_dims(image, axis=0)
        
        # Ensure image has the right number of channels
        input_channels = model.input_shape[-1]
        if image.shape[-1] != input_channels:
            if input_channels == 1 and image.shape[-1] == 3:
                # Convert RGB to grayscale
                image = np.mean(image, axis=-1, keepdims=True)
            elif input_channels == 3 and image.shape[-1] == 1:
                # Convert grayscale to RGB
                image = np.repeat(image, 3, axis=-1)
            else:
                raise ValueError(f"Cannot convert image with {image.shape[-1]} channels to {input_channels} channels")
        
        # Apply model-specific preprocessing
        if model_type == "typed":
            # Enhance contrast for typed text
            image = tf.image.adjust_contrast(image, 1.5)
        elif model_type == "handwritten":
            # Apply specific preprocessing for handwritten text
            # This might include different contrast/brightness adjustments
            image = tf.image.adjust_brightness(image, 0.1)
            image = tf.image.adjust_contrast(image, 1.2)
        elif model_type == "hybrid":
            # For hybrid text, use a balanced approach
            image = tf.image.adjust_contrast(image, 1.3)
        
        # Normalize image to [0, 1] if not already
        if isinstance(image, np.ndarray) and image.max() > 1.0:
            image = image / 255.0
        elif isinstance(image, tf.Tensor) and tf.reduce_max(image) > 1.0:
            image = image / 255.0
        
        # Convert TensorFlow tensor back to numpy if needed
        if isinstance(image, tf.Tensor):
            image = image.numpy()
        
        # Record preprocessing time
        metadata["preprocessing_time_ms"] = (time.time() - preprocess_start_time) * 1000
        
        # Run inference with GPU acceleration
        inference_start_time = time.time()
        
        # Use GPU if available
        if metadata["gpu_available"]:
            with tf.device('/GPU:0'):
                # Use TensorFlow's predict method with batching for efficiency
                output = model.predict(image, batch_size=batch_size, verbose=0)
                metadata["gpu_utilized"] = True
        else:
            # Fallback to CPU if GPU is not available
            logger.warning("GPU not available. Running inference on CPU which may be slower.")
            output = model.predict(image, batch_size=batch_size, verbose=0)
        
        # Record inference time
        metadata["inference_time_ms"] = (time.time() - inference_start_time) * 1000
        
        # Post-processing and confidence scoring
        postprocess_start_time = time.time()
        
        # Calculate confidence scores
        confidence_scores = calculate_confidence_scores(output, model_type, confidence_threshold)
        metadata["confidence_scores"] = confidence_scores
        
        # Flag for human review if needed
        metadata["requires_human_review"] = confidence_scores.get("requires_human_review", False)
        
        # Record postprocessing time
        metadata["postprocessing_time_ms"] = (time.time() - postprocess_start_time) * 1000
        metadata["total_time_ms"] = (time.time() - total_start_time) * 1000
        
        # Add performance metrics
        metadata["performance"] = {
            "images_per_second": batch_size / (metadata["inference_time_ms"] / 1000),
            "total_processing_time_ms": metadata["total_time_ms"],
        }
        
        return output, metadata
    
    except Exception as e:
        logger.error(f"Inference error: {str(e)}")
        metadata["error"] = str(e)
        metadata["requires_human_review"] = True  # Default to human review on error
        return None, metadata


def calculate_confidence_scores(output: np.ndarray, model_type: str, threshold: float = 0.75) -> Dict[str, Any]:
    """
    Calculate confidence scores for the model output and flag low-confidence fields.
    
    As specified in section 4.1.8 of the technical specification, the OCR service must
    implement confidence scoring for extracted fields and flag low-confidence fields
    for human verification.
    
    Args:
        output: Model output as numpy array
        model_type: Type of model (typed, handwritten, hybrid)
        threshold: Confidence threshold below which fields are flagged (default: 0.75)
    
    Returns:
        Dictionary containing:
            - Field-level confidence scores (0.0 to 1.0)
            - Overall confidence score
            - Flags for low-confidence fields
    """
    confidence_scores = {
        "fields": {},
        "overall": 0.0,
        "low_confidence_fields": [],
        "requires_human_review": False
    }
    
    try:
        # Different confidence calculation based on model type
        if model_type == "typed":
            # For typed text, confidence is typically higher
            if isinstance(output, np.ndarray):
                # Process character probabilities for typed text
                char_confidences = np.max(output, axis=-1)  # Max probability for each character
                
                # Calculate field-level confidences (assuming output structure has field information)
                # This is a simplified example - actual implementation would depend on model output format
                field_confidences = {
                    "text": float(np.mean(char_confidences)),
                    "date": float(np.mean(char_confidences[:10])) if len(char_confidences) > 10 else 0.9,
                    "amount": float(np.mean(char_confidences[-5:])) if len(char_confidences) > 5 else 0.85,
                }
                
                # Store field confidences
                confidence_scores["fields"] = field_confidences
                
                # Calculate overall confidence
                confidence_scores["overall"] = float(np.mean(list(field_confidences.values())))
                
                # Flag low-confidence fields
                for field, score in field_confidences.items():
                    if score < threshold:
                        confidence_scores["low_confidence_fields"].append(field)
                        confidence_scores["requires_human_review"] = True
        
        elif model_type == "handwritten":
            # For handwritten text, confidence calculation is typically more conservative
            if isinstance(output, np.ndarray):
                # Process character probabilities for handwritten text
                char_confidences = np.max(output, axis=-1)  # Max probability for each character
                
                # Apply a slightly lower threshold for handwritten text due to inherent variability
                adjusted_threshold = threshold * 0.9  # 10% lower threshold for handwritten text
                
                # Calculate field-level confidences
                field_confidences = {
                    "text": float(np.mean(char_confidences)),
                    "signature": float(np.mean(char_confidences[:20])) if len(char_confidences) > 20 else 0.8,
                    "name": float(np.mean(char_confidences[-10:])) if len(char_confidences) > 10 else 0.75,
                }
                
                # Store field confidences
                confidence_scores["fields"] = field_confidences
                
                # Calculate overall confidence
                confidence_scores["overall"] = float(np.mean(list(field_confidences.values())))
                
                # Flag low-confidence fields
                for field, score in field_confidences.items():
                    if score < adjusted_threshold:
                        confidence_scores["low_confidence_fields"].append(field)
                        confidence_scores["requires_human_review"] = True
        
        elif model_type == "hybrid":
            # For hybrid models, combine confidence calculations from both typed and handwritten
            if isinstance(output, np.ndarray):
                # This would depend on the specific hybrid model implementation
                # Assuming the model outputs separate confidences for typed and handwritten portions
                
                # Simplified example - in practice, this would be more sophisticated
                typed_portion = output[:len(output)//2]
                handwritten_portion = output[len(output)//2:]
                
                typed_confidence = float(np.mean(np.max(typed_portion, axis=-1)))
                handwritten_confidence = float(np.mean(np.max(handwritten_portion, axis=-1)))
                
                # Calculate field-level confidences
                field_confidences = {
                    "typed_text": typed_confidence,
                    "handwritten_text": handwritten_confidence,
                    "combined": (typed_confidence + handwritten_confidence) / 2
                }
                
                # Store field confidences
                confidence_scores["fields"] = field_confidences
                
                # Calculate overall confidence
                confidence_scores["overall"] = field_confidences["combined"]
                
                # Flag low-confidence fields
                for field, score in field_confidences.items():
                    if score < threshold:
                        confidence_scores["low_confidence_fields"].append(field)
                        confidence_scores["requires_human_review"] = True
        
        # Add metadata about confidence calculation
        confidence_scores["metadata"] = {
            "model_type": model_type,
            "threshold": threshold,
            "calculation_time": time.time(),
        }
    
    except Exception as e:
        logger.error(f"Error calculating confidence scores: {str(e)}")
        confidence_scores["error"] = str(e)
        confidence_scores["overall"] = 0.0
        confidence_scores["requires_human_review"] = True  # Default to human review on error
    
    return confidence_scores


def get_optimal_batch_size(model: tf.keras.Model, 
                          initial_batch_size: int = 1, 
                          max_batch_size: int = 16) -> int:
    """
    Determine the optimal batch size for inference based on available GPU memory.
    
    Args:
        model: TensorFlow model
        initial_batch_size: Starting batch size
        max_batch_size: Maximum batch size to try
    
    Returns:
        Optimal batch size for inference
    """
    try:
        # Get input shape from model
        input_shape = model.input_shape
        if input_shape[0] is None:  # Batch dimension is None
            # Create a sample shape with batch dimension
            sample_shape = list(input_shape)
            sample_shape[0] = 1  # Set batch dimension to 1
        else:
            sample_shape = input_shape
        
        # Try increasing batch sizes until we run out of memory
        optimal_batch_size = initial_batch_size
        
        for batch_size in range(initial_batch_size, max_batch_size + 1):
            try:
                # Create a sample input with the current batch size
                sample_shape_with_batch = list(sample_shape)
                sample_shape_with_batch[0] = batch_size
                sample_input = tf.random.normal(sample_shape_with_batch)
                
                # Try to run inference
                with tf.device('/GPU:0'):
                    _ = model(sample_input, training=False)
                
                # If successful, update optimal batch size
                optimal_batch_size = batch_size
                logger.debug(f"Batch size {batch_size} successful")
            
            except (tf.errors.ResourceExhaustedError, tf.errors.InternalError, tf.errors.UnknownError):
                # Out of memory or other GPU error
                logger.debug(f"Batch size {batch_size} failed due to resource constraints")
                break
            
            except Exception as e:
                logger.warning(f"Error testing batch size {batch_size}: {str(e)}")
                break
        
        logger.info(f"Determined optimal batch size: {optimal_batch_size}")
        return optimal_batch_size
    
    except Exception as e:
        logger.error(f"Error determining optimal batch size: {str(e)}")
        return initial_batch_size


def monitor_gpu_utilization() -> Dict[str, Any]:
    """
    Monitor GPU utilization during model inference.
    
    Returns:
        Dictionary with GPU utilization metrics
    """
    # This is a placeholder - in a production environment, you would use
    # nvidia-ml-py3 (pynvml) to get accurate GPU utilization metrics
    metrics = {
        "timestamp": time.time(),
        "gpus": {}
    }
    
    try:
        # Get list of GPUs
        gpus = tf.config.list_physical_devices('GPU')
        
        for i, gpu in enumerate(gpus):
            # In a real implementation, you would use pynvml to get:
            # - GPU utilization percentage
            # - Memory usage
            # - Temperature
            # - Power usage
            metrics["gpus"][i] = {
                "device": str(gpu),
                "memory_usage": "N/A",  # Would be actual memory usage in MB
                "utilization": "N/A",    # Would be utilization percentage
            }
    
    except Exception as e:
        logger.error(f"Error monitoring GPU utilization: {str(e)}")
        metrics["error"] = str(e)
    
    return metrics


def cleanup_gpu_memory() -> Dict[str, Any]:
    """
    Clean up GPU memory after model inference to prevent memory leaks.
    
    This function releases GPU memory by clearing the TensorFlow session and
    forcing garbage collection. It's important for long-running services to
    prevent memory leaks and ensure consistent performance.
    
    Returns:
        Dictionary with cleanup results and status
    """
    cleanup_results = {
        "success": False,
        "timestamp": time.time(),
        "actions_performed": []
    }
    
    try:
        # Get memory info before cleanup
        before_cleanup = get_available_vram()
        cleanup_results["before_cleanup_vram"] = before_cleanup
        
        # Clear TensorFlow session
        tf.keras.backend.clear_session()
        cleanup_results["actions_performed"].append("cleared_tf_session")
        
        # Reset GPU devices if possible
        try:
            for device in tf.config.list_physical_devices('GPU'):
                tf.config.experimental.reset_memory_stats(device)
            cleanup_results["actions_performed"].append("reset_gpu_memory_stats")
        except Exception as reset_error:
            logger.debug(f"Could not reset GPU memory stats: {str(reset_error)}")
        
        # Force garbage collection
        import gc
        gc.collect()
        cleanup_results["actions_performed"].append("forced_garbage_collection")
        
        # Get memory info after cleanup
        time.sleep(0.5)  # Brief pause to allow memory to be reclaimed
        after_cleanup = get_available_vram()
        cleanup_results["after_cleanup_vram"] = after_cleanup
        
        # Calculate memory freed
        if before_cleanup and after_cleanup:
            memory_freed = {}
            for gpu_id in before_cleanup:
                if gpu_id in after_cleanup:
                    memory_freed[gpu_id] = max(0, after_cleanup[gpu_id] - before_cleanup[gpu_id])
            
            cleanup_results["memory_freed_mb"] = memory_freed
            total_freed = sum(memory_freed.values())
            cleanup_results["total_memory_freed_mb"] = total_freed
            
            if total_freed > 0:
                logger.info(f"GPU memory cleanup freed approximately {total_freed}MB")
            else:
                logger.debug("GPU memory cleanup completed, but no significant memory was freed")
        else:
            logger.debug("GPU memory cleanup completed, but could not measure memory impact")
        
        cleanup_results["success"] = True
        return cleanup_results
    
    except Exception as e:
        logger.error(f"Error cleaning up GPU memory: {str(e)}")
        cleanup_results["error"] = str(e)
        return cleanup_results