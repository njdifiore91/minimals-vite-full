"""
Type definitions for OCR models used by the OCR Service.

This module provides type hints for representing different OCR models (typed, handwritten, hybrid),
their parameters, and selection logic. It includes types for model configuration, model selection,
and model results to ensure type safety throughout the OCR processing pipeline.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, TypedDict, Union

# Import TensorFlow type hints conditionally to avoid runtime dependency
# This allows the type definitions to be used without requiring TensorFlow to be installed
try:
    import tensorflow as tf
    TensorType = tf.Tensor
    ModelType = tf.keras.Model
except ImportError:
    # Define placeholder types if TensorFlow is not available
    class TensorType:
        pass
    
    class ModelType:
        pass


class OCRModelType(enum.Enum):
    """
    Types of OCR models supported by the service.
    
    These model types correspond to different OCR processing pipelines optimized
    for specific types of text and document formats.
    """
    
    TYPED = "typed"  # Model optimized for typed/printed text
    HANDWRITTEN = "handwritten"  # Model optimized for handwritten text
    HYBRID = "hybrid"  # Model that can handle both typed and handwritten text


class ModelParameters(TypedDict):
    """
    Parameters for configuring OCR models.
    
    This type defines the configuration parameters for OCR models, including
    model paths, input parameters, preprocessing options, and hardware acceleration settings.
    """
    
    # Model identification
    model_name: str  # Name of the model
    model_version: str  # Version of the model
    model_type: str  # Type of model (corresponds to OCRModelType values)
    
    # Model paths
    model_path: str  # Path to model weights file
    vocab_path: str  # Path to vocabulary file
    
    # Input parameters
    input_shape: Tuple[int, int, int]  # Expected input shape (height, width, channels)
    input_dtype: str  # Expected input data type (e.g., 'float32', 'uint8')
    max_text_length: int  # Maximum text length the model can handle
    
    # Preprocessing options
    grayscale: bool  # Whether to convert input to grayscale
    normalize_input: bool  # Whether to normalize input images
    
    # Processing parameters
    batch_size: int  # Batch size for processing
    use_gpu: bool  # Whether to use GPU acceleration
    gpu_memory_limit: Optional[int]  # GPU memory limit in MB
    num_threads: int  # Number of CPU threads to use
    
    # Model-specific parameters
    beam_width: int  # Beam width for beam search decoding
    language: str  # Language code (e.g., 'en', 'fr')
    confidence_threshold: float  # Minimum confidence threshold for accepting results


class ModelMetrics(TypedDict):
    """
    Performance metrics for OCR models.
    
    This type defines the performance metrics for evaluating OCR models,
    including accuracy, error rates, and processing time.
    """
    
    accuracy: float  # Overall accuracy of the model (0.0-1.0)
    character_error_rate: float  # Character error rate (lower is better)
    word_error_rate: float  # Word error rate (lower is better)
    processing_time: float  # Average processing time per page in seconds
    confidence_score: float  # Average confidence score (0.0-1.0)
    f1_score: float  # F1 score for text detection
    precision: float  # Precision for text detection
    recall: float  # Recall for text detection


class ModelResult(TypedDict):
    """
    Results of OCR model processing.
    
    This type represents the output of an OCR model after processing a document.
    """
    
    text: str  # Extracted text
    confidence: float  # Overall confidence score (0.0-1.0)
    bounding_boxes: List[Dict[str, Any]]  # Bounding boxes for text regions
    word_confidences: List[float]  # Confidence scores for individual words
    processing_time: float  # Time taken to process the document in seconds
    page_number: int  # Page number in multi-page documents
    model_type: str  # Type of model used for extraction
    warnings: List[str]  # Any warnings during processing
    language: str  # Detected or specified language


class ModelSelectionCriteria(TypedDict, total=False):
    """
    Criteria for selecting the appropriate OCR model.
    
    This type defines the criteria used to select the appropriate OCR model
    for a given document. The 'total=False' parameter indicates that all fields are optional.
    """
    
    document_type: str  # Type of document (e.g., 'application', 'tax_return')
    has_handwriting: Optional[bool]  # Whether the document contains handwriting
    image_quality: float  # Quality of the image (0.0-1.0)
    priority: str  # Processing priority ('high', 'medium', 'low')
    language: str  # Document language
    content_type: str  # MIME type of the document
    file_size: int  # Size of the document in bytes


class ModelSelector:
    """
    Utility class for selecting the appropriate OCR model based on document characteristics.
    
    This class provides methods for determining which OCR model type is most appropriate
    for a given document based on its characteristics and processing requirements.
    """
    
    @staticmethod
    def select_model_type(criteria: ModelSelectionCriteria) -> OCRModelType:
        """
        Select the appropriate OCR model type based on selection criteria.
        
        Args:
            criteria: Model selection criteria
            
        Returns:
            The selected OCR model type
        """
        # Check if handwriting is explicitly specified
        if criteria.get('has_handwriting') is not None:
            if criteria['has_handwriting']:
                return OCRModelType.HANDWRITTEN
            else:
                return OCRModelType.TYPED
        
        # Check document type
        document_type = criteria.get('document_type')
        if document_type:
            # Documents that typically contain handwriting
            handwritten_doc_types = ['application', 'id_document']
            if document_type.lower() in handwritten_doc_types:
                return OCRModelType.HYBRID
        
        # Default to hybrid model for maximum coverage
        return OCRModelType.HYBRID
    
    @staticmethod
    def get_default_parameters(model_type: OCRModelType) -> ModelParameters:
        """
        Get default parameters for the specified model type.
        
        Args:
            model_type: The OCR model type
            
        Returns:
            Default parameters for the specified model type
            
        Raises:
            ValueError: If the model type is not supported
        """
        if model_type == OCRModelType.TYPED:
            return DEFAULT_TYPED_MODEL_PARAMS
        elif model_type == OCRModelType.HANDWRITTEN:
            return DEFAULT_HANDWRITTEN_MODEL_PARAMS
        elif model_type == OCRModelType.HYBRID:
            return DEFAULT_HYBRID_MODEL_PARAMS
        else:
            raise ValueError(f"Unsupported model type: {model_type}")


class TensorFlowModel:
    """
    Wrapper class for TensorFlow models used in OCR processing.
    
    This class provides a consistent interface for working with TensorFlow models,
    handling model loading, preprocessing, inference, and result formatting.
    """
    
    def __init__(self, parameters: ModelParameters):
        """
        Initialize a TensorFlow model with the specified parameters.
        
        Args:
            parameters: Model parameters
        """
        self.parameters = parameters
        self.model = None
        self.metrics = None
    
    def load(self) -> bool:
        """
        Load the TensorFlow model from the specified path.
        
        Returns:
            True if the model was loaded successfully, False otherwise
        """
        if not self.parameters.get('model_path'):
            raise ValueError("Model path not specified")
        
        try:
            # Configure GPU memory growth to avoid OOM errors
            gpus = tf.config.experimental.list_physical_devices('GPU')
            if gpus and self.parameters.get('use_gpu', True):
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
                
                # Set memory limit if specified
                if self.parameters.get('gpu_memory_limit'):
                    tf.config.experimental.set_virtual_device_configuration(
                        gpus[0],
                        [tf.config.experimental.VirtualDeviceConfiguration(
                            memory_limit=self.parameters['gpu_memory_limit']
                        )]
                    )
                
                # Use mixed precision for better performance
                tf.keras.mixed_precision.set_global_policy('mixed_float16')
            
            # Load the model
            self.model = tf.keras.models.load_model(self.parameters['model_path'])
            return True
        except Exception as e:
            raise RuntimeError(f"Error loading model: {e}")
    
    def preprocess(self, image: Any) -> TensorType:
        """
        Preprocess an image for OCR.
        
        Args:
            image: Input image as a numpy array
            
        Returns:
            Preprocessed image as a TensorFlow tensor
        """
        # Convert to tensor
        tensor = tf.convert_to_tensor(image)
        
        # Resize if needed
        if self.parameters.get('input_shape'):
            height, width, channels = self.parameters['input_shape']
            tensor = tf.image.resize(tensor, [height, width])
        
        # Convert to grayscale if needed
        if self.parameters.get('grayscale', False) and tensor.shape[-1] == 3:
            tensor = tf.image.rgb_to_grayscale(tensor)
        
        # Normalize if needed
        if self.parameters.get('normalize_input', True):
            tensor = tensor / 255.0
        
        # Expand dimensions for batch
        tensor = tf.expand_dims(tensor, 0)
        
        return tensor
    
    def predict(self, input_tensor: TensorType) -> Dict[str, Any]:
        """
        Run inference on the preprocessed input.
        
        Args:
            input_tensor: Preprocessed input tensor
            
        Returns:
            Dictionary of prediction results
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        try:
            # Record start time for performance measurement
            start_time = datetime.now()
            
            # Run inference
            # The exact call depends on the model's signature
            if hasattr(self.model, 'signatures'):
                # SavedModel with signatures
                infer = self.model.signatures['serving_default']
                result = infer(input_tensor)
            else:
                # Regular Keras model
                result = self.model(input_tensor)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Post-process the results
            # This is a simplified example - actual implementation would depend on the model
            if isinstance(result, dict):
                predictions = result
            else:
                # Convert tensor output to dictionary
                predictions = {"output": result}
            
            # Add processing time to results
            predictions["processing_time"] = processing_time
            
            return predictions
        except Exception as e:
            raise RuntimeError(f"Prediction error: {e}")


# Default model parameters for different OCR model types

# Default parameters for typed text OCR
DEFAULT_TYPED_MODEL_PARAMS: ModelParameters = {
    'model_name': 'typed_text_ocr',
    'model_version': '1.0.0',
    'model_type': OCRModelType.TYPED.value,
    'model_path': '/models/typed_text_ocr',
    'vocab_path': '/models/typed_text_ocr/vocab.txt',
    'input_shape': (768, 768, 3),
    'input_dtype': 'float32',
    'max_text_length': 512,
    'grayscale': False,
    'normalize_input': True,
    'batch_size': 1,
    'use_gpu': True,
    'gpu_memory_limit': 4096,  # 4GB
    'num_threads': 4,
    'beam_width': 5,
    'language': 'en',
    'confidence_threshold': 0.7,
}

# Default parameters for handwritten text OCR
DEFAULT_HANDWRITTEN_MODEL_PARAMS: ModelParameters = {
    'model_name': 'handwritten_text_ocr',
    'model_version': '1.0.0',
    'model_type': OCRModelType.HANDWRITTEN.value,
    'model_path': '/models/handwritten_text_ocr',
    'vocab_path': '/models/handwritten_text_ocr/vocab.txt',
    'input_shape': (1024, 1024, 3),
    'input_dtype': 'float32',
    'max_text_length': 512,
    'grayscale': True,
    'normalize_input': True,
    'batch_size': 1,
    'use_gpu': True,
    'gpu_memory_limit': 6144,  # 6GB
    'num_threads': 4,
    'beam_width': 10,
    'language': 'en',
    'confidence_threshold': 0.6,
}

# Default parameters for hybrid text OCR
DEFAULT_HYBRID_MODEL_PARAMS: ModelParameters = {
    'model_name': 'hybrid_text_ocr',
    'model_version': '1.0.0',
    'model_type': OCRModelType.HYBRID.value,
    'model_path': '/models/hybrid_text_ocr',
    'vocab_path': '/models/hybrid_text_ocr/vocab.txt',
    'input_shape': (1280, 1280, 3),
    'input_dtype': 'float32',
    'max_text_length': 768,
    'grayscale': False,
    'normalize_input': True,
    'batch_size': 1,
    'use_gpu': True,
    'gpu_memory_limit': 8192,  # 8GB
    'num_threads': 8,
    'beam_width': 15,
    'language': 'en',
    'confidence_threshold': 0.65,
}