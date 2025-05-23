# tensorflow_utils.py
# Utility functions for TensorFlow model loading, inference, and GPU management

import os
import json
import time
import logging
import tensorflow as tf
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any
from pathlib import Path

# Configure logger
logger = logging.getLogger(__name__)

# Constants
MODEL_VERSION_FILE = "model_version.json"
GPU_MEMORY_LIMIT = 0.9  # Use 90% of available GPU memory by default
MODEL_TYPES = ["typed", "handwritten", "hybrid", "structure"]


def configure_gpu_memory(memory_limit: float = GPU_MEMORY_LIMIT) -> None:
    """
    Configure TensorFlow to use a percentage of available GPU memory to prevent OOM errors.
    
    Args:
        memory_limit: Fraction of GPU memory to allocate (0.0 to 1.0)
    """
    try:
        gpus = tf.config.list_physical_devices('GPU')
        if not gpus:
            logger.warning("No GPU found. Running on CPU which will be significantly slower.")
            return
        
        logger.info(f"Found {len(gpus)} GPU(s). Configuring memory growth.")
        
        # Configure memory growth for all GPUs
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
            
            # Set memory limit if specified
            if memory_limit < 1.0:
                gpu_memory = tf.config.experimental.get_memory_info(gpu)['total'] if hasattr(tf.config.experimental, 'get_memory_info') else None
                if gpu_memory:
                    memory_limit_bytes = int(gpu_memory * memory_limit)
                    tf.config.set_logical_device_configuration(
                        gpu,
                        [tf.config.LogicalDeviceConfiguration(memory_limit=memory_limit_bytes)]
                    )
                    logger.info(f"GPU {gpu.name} memory limited to {memory_limit*100:.0f}% ({memory_limit_bytes/(1024**3):.2f} GB)")
                else:
                    logger.info(f"GPU {gpu.name} memory growth enabled but limit not set (memory info not available)")
            else:
                logger.info(f"GPU {gpu.name} memory growth enabled without specific limit")
                
    except Exception as e:
        logger.error(f"Error configuring GPU memory: {str(e)}")
        logger.warning("Falling back to CPU. OCR performance will be degraded.")


def get_available_gpu_memory() -> Dict[str, float]:
    """
    Get available memory for each GPU in GB.
    
    Returns:
        Dictionary mapping GPU device names to available memory in GB
    """
    memory_info = {}
    try:
        gpus = tf.config.list_physical_devices('GPU')
        for i, gpu in enumerate(gpus):
            try:
                # Get memory info if available in this TF version
                if hasattr(tf.config.experimental, 'get_memory_info'):
                    info = tf.config.experimental.get_memory_info(gpu)
                    total = info['total'] / (1024**3)  # Convert to GB
                    used = info['used'] / (1024**3)    # Convert to GB
                    available = total - used
                    memory_info[gpu.name] = available
                else:
                    # If get_memory_info is not available, use a placeholder
                    memory_info[gpu.name] = -1.0  # Indicates memory info not available
            except Exception as e:
                logger.warning(f"Could not get memory info for GPU {i}: {str(e)}")
                memory_info[gpu.name] = -1.0
    except Exception as e:
        logger.error(f"Error getting GPU memory info: {str(e)}")
    
    return memory_info


def check_gpu_requirements(min_vram_gb: float = 8.0) -> bool:
    """
    Check if the system meets the GPU requirements for OCR processing.
    
    Args:
        min_vram_gb: Minimum required VRAM in GB
        
    Returns:
        True if requirements are met, False otherwise
    """
    try:
        gpus = tf.config.list_physical_devices('GPU')
        if not gpus:
            logger.warning("No GPU found. OCR processing requires GPU acceleration.")
            return False
        
        # Check CUDA availability
        if not tf.test.is_built_with_cuda():
            logger.warning("TensorFlow not built with CUDA support. OCR performance will be degraded.")
            return False
        
        # Check available memory
        memory_info = get_available_gpu_memory()
        for gpu_name, memory_gb in memory_info.items():
            if memory_gb == -1.0:
                logger.warning(f"Could not determine memory for {gpu_name}. Assuming requirements are met.")
                continue
            
            if memory_gb < min_vram_gb:
                logger.warning(f"Insufficient VRAM on {gpu_name}: {memory_gb:.2f}GB available, {min_vram_gb}GB required")
                return False
        
        return True
    except Exception as e:
        logger.error(f"Error checking GPU requirements: {str(e)}")
        return False


def get_model_version(model_dir: str) -> Dict[str, Any]:
    """
    Get the version information for a model.
    
    Args:
        model_dir: Directory containing the model
        
    Returns:
        Dictionary with model version information
    """
    version_file = os.path.join(model_dir, MODEL_VERSION_FILE)
    try:
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"No version file found at {version_file}")
            return {
                "version": "unknown",
                "date_trained": "unknown",
                "accuracy": "unknown",
                "framework_version": "unknown"
            }
    except Exception as e:
        logger.error(f"Error reading model version: {str(e)}")
        return {
            "version": "error",
            "date_trained": "error",
            "accuracy": "error",
            "framework_version": "error",
            "error": str(e)
        }


def validate_model_compatibility(model_dir: str) -> bool:
    """
    Validate that the model is compatible with the current TensorFlow version.
    
    Args:
        model_dir: Directory containing the model
        
    Returns:
        True if compatible, False otherwise
    """
    try:
        version_info = get_model_version(model_dir)
        
        # Check if model was trained with a compatible TensorFlow version
        if "framework_version" in version_info and version_info["framework_version"] != "unknown":
            model_tf_version = version_info["framework_version"]
            current_tf_version = tf.__version__
            
            # Parse versions for comparison
            model_major, model_minor = map(int, model_tf_version.split('.')[:2])
            current_major, current_minor = map(int, current_tf_version.split('.')[:2])
            
            # Check compatibility (same major version, current minor >= model minor)
            if current_major != model_major or current_minor < model_minor:
                logger.warning(f"Model trained with TensorFlow {model_tf_version}, current version is {current_tf_version}")
                logger.warning("Model may not be compatible with current TensorFlow version")
                return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating model compatibility: {str(e)}")
        return False


def load_model(model_dir: str, model_type: str) -> Optional[tf.keras.Model]:
    """
    Load a TensorFlow model for OCR processing.
    
    Args:
        model_dir: Base directory containing model subdirectories
        model_type: Type of model to load (typed, handwritten, hybrid, structure)
        
    Returns:
        Loaded TensorFlow model or None if loading fails
    """
    if model_type not in MODEL_TYPES:
        logger.error(f"Invalid model type: {model_type}. Must be one of {MODEL_TYPES}")
        return None
    
    full_model_path = os.path.join(model_dir, model_type)
    
    try:
        # Check if model exists
        if not os.path.exists(full_model_path):
            logger.error(f"Model not found at {full_model_path}")
            return None
        
        # Validate model compatibility
        if not validate_model_compatibility(full_model_path):
            logger.warning(f"Model compatibility check failed for {model_type} model")
            # Continue loading anyway, but with a warning
        
        # Log model version information
        version_info = get_model_version(full_model_path)
        logger.info(f"Loading {model_type} model version {version_info.get('version', 'unknown')}")
        
        # Load the model
        start_time = time.time()
        model = tf.keras.models.load_model(full_model_path)
        load_time = time.time() - start_time
        
        logger.info(f"Successfully loaded {model_type} model in {load_time:.2f} seconds")
        return model
    
    except Exception as e:
        logger.error(f"Error loading {model_type} model: {str(e)}")
        return None


def load_all_models(model_dir: str) -> Dict[str, tf.keras.Model]:
    """
    Load all OCR models from the specified directory.
    
    Args:
        model_dir: Base directory containing model subdirectories
        
    Returns:
        Dictionary mapping model types to loaded models
    """
    models = {}
    for model_type in MODEL_TYPES:
        model = load_model(model_dir, model_type)
        if model is not None:
            models[model_type] = model
    
    if not models:
        logger.error("Failed to load any OCR models")
    else:
        logger.info(f"Successfully loaded {len(models)} OCR models")
    
    return models


def preprocess_image_for_ocr(image: np.ndarray, model_type: str) -> np.ndarray:
    """
    Preprocess an image for OCR inference based on model type.
    
    Args:
        image: Input image as numpy array
        model_type: Type of OCR model (typed, handwritten, hybrid, structure)
        
    Returns:
        Preprocessed image ready for model inference
    """
    if model_type not in MODEL_TYPES:
        logger.error(f"Invalid model type for preprocessing: {model_type}")
        return image
    
    try:
        # Common preprocessing steps
        # Convert to float32 and normalize to [0, 1]
        image = image.astype(np.float32) / 255.0
        
        # Model-specific preprocessing
        if model_type == "typed":
            # For typed text models: enhance contrast, resize to model input size
            # Assuming model input size is 1024x768 for typed text
            image = tf.image.resize(image, [768, 1024])
            image = tf.image.per_image_standardization(image)
            
        elif model_type == "handwritten":
            # For handwritten text models: different preprocessing may be needed
            # Assuming model input size is 1280x800 for handwritten text
            image = tf.image.resize(image, [800, 1280])
            # Apply specific preprocessing for handwritten text if needed
            
        elif model_type == "hybrid":
            # For hybrid models: general preprocessing that works for both types
            # Assuming model input size is 1280x800 for hybrid model
            image = tf.image.resize(image, [800, 1280])
            image = tf.image.per_image_standardization(image)
            
        elif model_type == "structure":
            # For structure recognition: preserve aspect ratio, pad if needed
            # Assuming model input size is 1600x1600 for structure model
            original_height, original_width = image.shape[:2]
            target_size = 1600
            
            # Preserve aspect ratio
            if original_height > original_width:
                new_height = target_size
                new_width = int(original_width * (target_size / original_height))
            else:
                new_width = target_size
                new_height = int(original_height * (target_size / original_width))
            
            # Resize while preserving aspect ratio
            image = tf.image.resize(image, [new_height, new_width])
            
            # Pad to square if needed
            if new_height < target_size or new_width < target_size:
                padded_image = np.zeros((target_size, target_size, image.shape[2]), dtype=np.float32)
                padded_image[:new_height, :new_width, :] = image.numpy()
                image = padded_image
        
        # Expand dimensions to create batch of size 1
        image = np.expand_dims(image, axis=0)
        
        return image
    
    except Exception as e:
        logger.error(f"Error preprocessing image for {model_type} model: {str(e)}")
        # Return original image expanded to batch dimension as fallback
        return np.expand_dims(image.astype(np.float32) / 255.0, axis=0)


def run_inference(model: tf.keras.Model, image: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Run inference on a preprocessed image using the specified model.
    
    Args:
        model: TensorFlow model to use for inference
        image: Preprocessed image as numpy array with batch dimension
        
    Returns:
        Tuple of (model output, inference time in seconds)
    """
    try:
        # Ensure image has batch dimension
        if len(image.shape) == 3:
            image = np.expand_dims(image, axis=0)
        
        # Run inference with timing
        start_time = time.time()
        output = model.predict(image)
        inference_time = time.time() - start_time
        
        return output, inference_time
    
    except Exception as e:
        logger.error(f"Error during model inference: {str(e)}")
        return None, 0.0


def calculate_confidence_scores(model_output: np.ndarray, model_type: str) -> Dict[str, float]:
    """
    Calculate confidence scores for OCR results based on model output.
    
    Args:
        model_output: Raw output from the OCR model
        model_type: Type of OCR model used
        
    Returns:
        Dictionary mapping field names to confidence scores (0.0 to 1.0)
    """
    try:
        # This is a simplified implementation - actual confidence scoring would depend on model architecture
        # and output format, which would be specific to the trained models
        
        # For demonstration, we'll return a placeholder implementation
        if model_type == "typed":
            # For typed text, confidence might be based on character recognition probabilities
            # This is a placeholder - actual implementation would process model_output
            return {
                "overall": 0.95,  # Overall document confidence
                "text_recognition": 0.97,  # Text recognition confidence
                "field_extraction": 0.93,  # Field extraction confidence
            }
            
        elif model_type == "handwritten":
            # For handwritten text, confidence might be lower
            # This is a placeholder - actual implementation would process model_output
            return {
                "overall": 0.85,  # Overall document confidence
                "text_recognition": 0.82,  # Text recognition confidence
                "field_extraction": 0.88,  # Field extraction confidence
            }
            
        elif model_type == "hybrid":
            # For hybrid text, confidence might be a weighted average
            # This is a placeholder - actual implementation would process model_output
            return {
                "overall": 0.90,  # Overall document confidence
                "text_recognition": 0.92,  # Text recognition confidence
                "field_extraction": 0.89,  # Field extraction confidence
            }
            
        elif model_type == "structure":
            # For structure recognition, confidence might be based on layout detection
            # This is a placeholder - actual implementation would process model_output
            return {
                "overall": 0.94,  # Overall document confidence
                "layout_detection": 0.96,  # Layout detection confidence
                "table_recognition": 0.92,  # Table recognition confidence
                "form_field_detection": 0.93,  # Form field detection confidence
            }
            
        else:
            logger.warning(f"Unknown model type for confidence scoring: {model_type}")
            return {"overall": 0.5}  # Default fallback
    
    except Exception as e:
        logger.error(f"Error calculating confidence scores: {str(e)}")
        return {"overall": 0.0, "error": str(e)}


def get_field_confidence(field_name: str, field_value: str, model_output: np.ndarray, model_type: str) -> float:
    """
    Calculate confidence score for a specific extracted field.
    
    Args:
        field_name: Name of the extracted field
        field_value: Extracted value for the field
        model_output: Raw output from the OCR model
        model_type: Type of OCR model used
        
    Returns:
        Confidence score for the field (0.0 to 1.0)
    """
    try:
        # This is a simplified implementation - actual field confidence scoring would be model-specific
        # and would analyze the specific regions/tokens in the model output corresponding to this field
        
        # For demonstration, we'll return values based on field characteristics
        
        # Base confidence starts high
        base_confidence = 0.95
        
        # Adjust based on field value characteristics
        if not field_value:  # Empty field
            return 0.0
        
        # Longer values might have lower confidence
        length_factor = max(0.0, 1.0 - (len(field_value) / 200))  # Penalize very long fields
        
        # Special characters might reduce confidence
        special_chars = sum(1 for c in field_value if not c.isalnum() and not c.isspace())
        special_char_factor = max(0.0, 1.0 - (special_chars / len(field_value) / 2))
        
        # Numeric fields might have higher confidence for typed text
        numeric_factor = 1.05 if field_value.isdigit() and model_type == "typed" else 1.0
        
        # Handwritten text generally has lower confidence
        model_factor = 0.9 if model_type == "handwritten" else 1.0
        
        # Calculate final confidence
        confidence = base_confidence * length_factor * special_char_factor * numeric_factor * model_factor
        
        # Ensure confidence is in [0, 1] range
        return max(0.0, min(1.0, confidence))
    
    except Exception as e:
        logger.error(f"Error calculating field confidence for {field_name}: {str(e)}")
        return 0.5  # Default medium confidence on error


def monitor_gpu_utilization() -> Dict[str, Any]:
    """
    Monitor GPU utilization and memory usage.
    
    Returns:
        Dictionary with GPU utilization metrics
    """
    try:
        # This requires nvidia-smi and pynvml to be properly installed
        # For a production system, you would use a more robust monitoring solution
        
        # Try to import pynvml for NVIDIA GPU monitoring
        try:
            import pynvml
            pynvml.nvmlInit()
            
            metrics = {}
            device_count = pynvml.nvmlDeviceGetCount()
            
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                
                metrics[f"gpu_{i}"] = {
                    "name": name,
                    "memory_used_gb": memory.used / (1024**3),
                    "memory_total_gb": memory.total / (1024**3),
                    "memory_percent": memory.used / memory.total * 100,
                    "gpu_utilization": utilization.gpu,
                    "memory_utilization": utilization.memory
                }
            
            pynvml.nvmlShutdown()
            return metrics
            
        except ImportError:
            # Fall back to TensorFlow memory info if pynvml is not available
            memory_info = get_available_gpu_memory()
            return {"memory_info": memory_info, "note": "Limited metrics available without pynvml"}
    
    except Exception as e:
        logger.error(f"Error monitoring GPU utilization: {str(e)}")
        return {"error": str(e)}


def optimize_model_for_inference(model: tf.keras.Model) -> tf.keras.Model:
    """
    Optimize a TensorFlow model for inference performance.
    
    Args:
        model: TensorFlow model to optimize
        
    Returns:
        Optimized model for inference
    """
    try:
        # Convert to TensorFlow Lite model for faster inference
        # Note: This is a simplified example - actual optimization would depend on deployment requirements
        
        # For TF 2.x models, we can use the TF-TRT (TensorRT) integration for GPU acceleration
        # This requires TensorRT to be installed
        try:
            from tensorflow.python.compiler.tensorrt import trt_convert as trt
            
            logger.info("Optimizing model with TensorRT...")
            
            # Save original model to temporary file
            temp_model_dir = os.path.join(os.getcwd(), "temp_model")
            os.makedirs(temp_model_dir, exist_ok=True)
            model.save(temp_model_dir)
            
            # Convert with TensorRT
            conversion_params = trt.TrtConversionParams(
                precision_mode=trt.TrtPrecisionMode.FP16,  # Use FP16 for faster inference
                max_workspace_size_bytes=8000000000,  # 8GB workspace
                maximum_cached_engines=1
            )
            
            converter = trt.TrtGraphConverterV2(
                input_saved_model_dir=temp_model_dir,
                conversion_params=conversion_params
            )
            
            # Convert and save optimized model
            converter.convert()
            optimized_model_dir = os.path.join(os.getcwd(), "optimized_model")
            os.makedirs(optimized_model_dir, exist_ok=True)
            converter.save(optimized_model_dir)
            
            # Load optimized model
            optimized_model = tf.saved_model.load(optimized_model_dir)
            logger.info("Model successfully optimized with TensorRT")
            
            # Clean up temporary directories
            import shutil
            shutil.rmtree(temp_model_dir, ignore_errors=True)
            
            # Return a callable function that wraps the optimized model
            # This maintains the same interface as the original model
            class OptimizedModel(tf.keras.Model):
                def __init__(self, trt_model):
                    super(OptimizedModel, self).__init__()
                    self.trt_model = trt_model
                    
                def call(self, inputs):
                    return self.trt_model(inputs)
                
                def predict(self, inputs):
                    return self.trt_model(inputs)
            
            return OptimizedModel(optimized_model)
            
        except (ImportError, tf.errors.NotFoundError) as e:
            logger.warning(f"TensorRT optimization not available: {str(e)}")
            logger.info("Falling back to standard TensorFlow optimization")
            
            # Standard TensorFlow optimization
            # Convert variables to constants for faster inference
            logger.info("Optimizing model with TensorFlow constant folding...")
            optimized_model = tf.function(lambda x: model(x))
            optimized_model = optimized_model.get_concrete_function(
                tf.TensorSpec([1, None, None, 3], model.inputs[0].dtype)
            )
            
            frozen_func = tf.python.framework.convert_to_constants.convert_variables_to_constants_v2(optimized_model)
            logger.info(f"Frozen model inputs: {[input.name for input in frozen_func.inputs]}")
            logger.info(f"Frozen model outputs: {[output.name for output in frozen_func.outputs]}")
            
            # Wrap the frozen graph in a callable class with the same interface
            class OptimizedModel(tf.keras.Model):
                def __init__(self, frozen_func):
                    super(OptimizedModel, self).__init__()
                    self.frozen_func = frozen_func
                    
                def call(self, inputs):
                    return self.frozen_func(inputs)
                
                def predict(self, inputs):
                    return self.frozen_func(inputs)[0]
            
            return OptimizedModel(frozen_func)
    
    except Exception as e:
        logger.error(f"Error optimizing model: {str(e)}")
        logger.warning("Returning original unoptimized model")
        return model


def get_model_metadata(model: tf.keras.Model) -> Dict[str, Any]:
    """
    Get metadata about a TensorFlow model.
    
    Args:
        model: TensorFlow model
        
    Returns:
        Dictionary with model metadata
    """
    try:
        metadata = {
            "input_shapes": [],
            "output_shapes": [],
            "parameter_count": 0,
            "layers": []
        }
        
        # Get input and output shapes
        for input_tensor in model.inputs:
            metadata["input_shapes"].append({
                "name": input_tensor.name,
                "shape": input_tensor.shape.as_list(),
                "dtype": input_tensor.dtype.name
            })
        
        for output_tensor in model.outputs:
            metadata["output_shapes"].append({
                "name": output_tensor.name,
                "shape": output_tensor.shape.as_list(),
                "dtype": output_tensor.dtype.name
            })
        
        # Get parameter count
        metadata["parameter_count"] = model.count_params()
        
        # Get layer information
        for layer in model.layers:
            layer_info = {
                "name": layer.name,
                "type": layer.__class__.__name__,
                "parameters": layer.count_params(),
                "output_shape": layer.output_shape if hasattr(layer, 'output_shape') else None
            }
            metadata["layers"].append(layer_info)
        
        return metadata
    
    except Exception as e:
        logger.error(f"Error getting model metadata: {str(e)}")
        return {"error": str(e)}