"""Type definitions for OCR models used by the OCR Service.

This module provides type hints for OCR models, model parameters, and model selection
used by the OCR Service. It includes types for different OCR models (typed, handwritten, hybrid)
and their parameters, as well as model selection logic based on document type.

The OCR Service uses TensorFlow for text recognition with GPU acceleration for performance.
"""

from __future__ import annotations

import enum
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, ClassVar, Type, Callable

# Import TensorFlow type hints conditionally to avoid runtime dependency
try:
    import tensorflow as tf
    TensorType = tf.Tensor
    TensorFlowModelType = tf.keras.Model
except ImportError:
    # Define placeholder types if TensorFlow is not available
    class TensorType:
        pass
    
    class TensorFlowModelType:
        pass


class OCRModelType(enum.Enum):
    """Types of OCR models supported by the OCR Service.
    
    These model types correspond to different text recognition scenarios:
    - TYPED: For documents with machine-printed text (invoices, tax forms)
    - HANDWRITTEN: For documents with handwritten text (forms, notes)
    - HYBRID: For documents with both typed and handwritten text (applications)
    """
    
    TYPED = "typed"
    HANDWRITTEN = "handwritten"
    HYBRID = "hybrid"
    
    @classmethod
    def from_string(cls, model_type: str) -> 'OCRModelType':
        """Convert a string to OCRModelType.
        
        Args:
            model_type: String representation of model type
            
        Returns:
            OCRModelType enum value
            
        Raises:
            ValueError: If the string doesn't match any model type
        """
        try:
            return cls(model_type.lower())
        except ValueError:
            valid_types = [t.value for t in cls]
            raise ValueError(f"Invalid model type: {model_type}. Valid types are: {valid_types}")


@dataclass
class ModelParameters:
    """Parameters for configuring OCR models.
    
    This class represents the configuration parameters for OCR models,
    including hyperparameters, preprocessing options, and hardware acceleration settings.
    
    Attributes:
        model_type: Type of OCR model (typed, handwritten, hybrid)
        model_id: Unique identifier for the model
        model_version: Version of the model
        batch_size: Batch size for inference
        image_height: Input image height for the model
        image_width: Input image width for the model
        channels: Number of image channels (1 for grayscale, 3 for RGB)
        use_gpu: Whether to use GPU acceleration
        gpu_memory_limit: GPU memory limit in MB (None for no limit)
        precision: Numerical precision for model inference (float32, float16, int8)
        confidence_threshold: Minimum confidence threshold for valid predictions
        preprocessing_steps: List of preprocessing steps to apply
        postprocessing_steps: List of postprocessing steps to apply
        language: Primary language for the model
        additional_languages: Additional supported languages
        timeout_ms: Timeout for model inference in milliseconds
        max_retry_attempts: Maximum number of retry attempts for failed inference
    """
    
    model_type: OCRModelType
    model_id: str
    model_version: str
    batch_size: int = 1
    image_height: int = 1024
    image_width: int = 1024
    channels: int = 3
    use_gpu: bool = True
    gpu_memory_limit: Optional[int] = None  # in MB
    precision: str = "float32"  # float32, float16, int8
    confidence_threshold: float = 0.7
    preprocessing_steps: List[str] = field(default_factory=list)
    postprocessing_steps: List[str] = field(default_factory=list)
    language: str = "en"
    additional_languages: List[str] = field(default_factory=list)
    timeout_ms: int = 30000  # 30 seconds
    max_retry_attempts: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parameters to dictionary.
        
        Returns:
            Dictionary representation of parameters
        """
        return {
            "model_type": self.model_type.value,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "batch_size": self.batch_size,
            "image_height": self.image_height,
            "image_width": self.image_width,
            "channels": self.channels,
            "use_gpu": self.use_gpu,
            "gpu_memory_limit": self.gpu_memory_limit,
            "precision": self.precision,
            "confidence_threshold": self.confidence_threshold,
            "preprocessing_steps": self.preprocessing_steps,
            "postprocessing_steps": self.postprocessing_steps,
            "language": self.language,
            "additional_languages": self.additional_languages,
            "timeout_ms": self.timeout_ms,
            "max_retry_attempts": self.max_retry_attempts
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelParameters':
        """Create parameters from dictionary.
        
        Args:
            data: Dictionary representation of parameters
            
        Returns:
            ModelParameters instance
        """
        # Convert string model_type to enum
        if "model_type" in data and isinstance(data["model_type"], str):
            data["model_type"] = OCRModelType.from_string(data["model_type"])
            
        return cls(**data)
    
    @classmethod
    def from_json_file(cls, file_path: Union[str, Path]) -> 'ModelParameters':
        """Load parameters from JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            ModelParameters instance
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file contains invalid JSON
        """
        file_path = Path(file_path)
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class ModelMetrics:
    """Performance metrics for OCR models.
    
    This class represents performance metrics for OCR models,
    including accuracy, processing time, and resource usage.
    
    Attributes:
        character_accuracy: Character-level accuracy (0.0-1.0)
        word_accuracy: Word-level accuracy (0.0-1.0)
        line_accuracy: Line-level accuracy (0.0-1.0)
        average_confidence: Average confidence score across predictions
        processing_time_ms: Average processing time per image in milliseconds
        memory_usage_mb: Peak memory usage in megabytes
        gpu_memory_usage_mb: Peak GPU memory usage in megabytes
        throughput_images_per_second: Processing throughput in images per second
        error_rate: Error rate (1.0 - accuracy)
        confusion_matrix: Character confusion matrix
        timestamp: When these metrics were collected
    """
    
    character_accuracy: float
    word_accuracy: float
    line_accuracy: float
    average_confidence: float
    processing_time_ms: float
    memory_usage_mb: float
    gpu_memory_usage_mb: Optional[float] = None
    throughput_images_per_second: float = 0.0
    error_rate: float = 0.0
    confusion_matrix: Dict[str, Dict[str, int]] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary.
        
        Returns:
            Dictionary representation of metrics
        """
        return {
            "character_accuracy": self.character_accuracy,
            "word_accuracy": self.word_accuracy,
            "line_accuracy": self.line_accuracy,
            "average_confidence": self.average_confidence,
            "processing_time_ms": self.processing_time_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "gpu_memory_usage_mb": self.gpu_memory_usage_mb,
            "throughput_images_per_second": self.throughput_images_per_second,
            "error_rate": self.error_rate,
            "confusion_matrix": self.confusion_matrix,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelMetrics':
        """Create metrics from dictionary.
        
        Args:
            data: Dictionary representation of metrics
            
        Returns:
            ModelMetrics instance
        """
        # Convert ISO timestamp string to datetime
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
            
        return cls(**data)
    
    def get_top_confusions(self, limit: int = 10) -> List[Tuple[str, str, int]]:
        """Get the top character confusions.
        
        Args:
            limit: Maximum number of confusions to return
            
        Returns:
            List of (expected, predicted, count) tuples
        """
        confusions = []
        for expected, predictions in self.confusion_matrix.items():
            for predicted, count in predictions.items():
                if expected != predicted:  # Only include actual confusions
                    confusions.append((expected, predicted, count))
        
        # Sort by count in descending order
        confusions.sort(key=lambda x: x[2], reverse=True)
        
        return confusions[:limit]


@dataclass
class ModelResult:
    """Result of running an OCR model on input data.
    
    This class represents the result of running an OCR model on input data,
    including the extracted text, confidence scores, and processing metadata.
    
    Attributes:
        model_id: ID of the model used
        model_type: Type of model used
        text: Extracted text
        confidence: Overall confidence score
        word_confidences: Confidence scores for individual words
        processing_time_ms: Time taken to process the input in milliseconds
        timestamp: When the processing was completed
        page_number: Page number in multi-page document (0-based)
        total_pages: Total number of pages in the document
        image_dimensions: Dimensions of the input image (width, height)
        warnings: Warnings generated during processing
        error: Error message if processing failed
    """
    
    model_id: str
    model_type: OCRModelType
    text: str
    confidence: float
    word_confidences: Dict[str, float] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    page_number: int = 0
    total_pages: int = 1
    image_dimensions: Tuple[int, int] = (0, 0)  # (width, height)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        """Check if the model processing was successful.
        
        Returns:
            True if processing was successful, False otherwise
        """
        return self.error is None
    
    @property
    def is_low_confidence(self) -> bool:
        """Check if the result has low confidence.
        
        Returns:
            True if confidence is below 0.7, False otherwise
        """
        return self.confidence < 0.7
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary.
        
        Returns:
            Dictionary representation of result
        """
        return {
            "model_id": self.model_id,
            "model_type": self.model_type.value,
            "text": self.text,
            "confidence": self.confidence,
            "word_confidences": self.word_confidences,
            "processing_time_ms": self.processing_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "page_number": self.page_number,
            "total_pages": self.total_pages,
            "image_dimensions": self.image_dimensions,
            "warnings": self.warnings,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelResult':
        """Create result from dictionary.
        
        Args:
            data: Dictionary representation of result
            
        Returns:
            ModelResult instance
        """
        # Convert string model_type to enum
        if "model_type" in data and isinstance(data["model_type"], str):
            data["model_type"] = OCRModelType.from_string(data["model_type"])
            
        # Convert ISO timestamp string to datetime
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
            
        return cls(**data)
    
    @classmethod
    def error_result(cls, model_id: str, model_type: OCRModelType, error_message: str) -> 'ModelResult':
        """Create an error result.
        
        Args:
            model_id: ID of the model
            model_type: Type of model
            error_message: Error message
            
        Returns:
            ModelResult instance representing an error
        """
        return cls(
            model_id=model_id,
            model_type=model_type,
            text="",
            confidence=0.0,
            error=error_message
        )


class ModelSelection:
    """Utility class for selecting appropriate OCR models based on document type.
    
    This class provides methods for selecting the appropriate OCR model
    based on document type and content characteristics.
    """
    
    # Default model mappings by document type
    # Each document type has mappings for typed, handwritten, and hybrid models,
    # as well as a default model to use if content type is unknown
    _MODEL_MAPPINGS: ClassVar[Dict[str, Dict[str, str]]] = {
        "application_form": {
            "typed_model_id": "typed_text_default",
            "handwritten_model_id": "handwritten_text_default",
            "hybrid_model_id": "hybrid_text_default",
            "default_model_id": "hybrid_text_default"
        },
        "tax_return": {
            "typed_model_id": "typed_text_default",
            "handwritten_model_id": "handwritten_text_default",
            "hybrid_model_id": "hybrid_text_default",
            "default_model_id": "typed_text_default"
        },
        "bank_statement": {
            "typed_model_id": "typed_text_default",
            "handwritten_model_id": "handwritten_text_default",
            "hybrid_model_id": "hybrid_text_default",
            "default_model_id": "typed_text_default"
        },
        "identity_document": {
            "typed_model_id": "typed_text_default",
            "handwritten_model_id": "handwritten_text_default",
            "hybrid_model_id": "hybrid_text_default",
            "default_model_id": "hybrid_text_default"
        }
    }
    
    @classmethod
    def get_model_id(cls, document_type: str, content_type: Optional[OCRModelType] = None) -> str:
        """Get the appropriate model ID for a document type and content type.
        
        Args:
            document_type: Type of document
            content_type: Type of content (typed, handwritten, hybrid)
            
        Returns:
            Model ID to use
            
        Raises:
            ValueError: If the document type is unknown
        """
        # Get model mapping for document type, or use application_form as fallback
        model_mapping = cls._MODEL_MAPPINGS.get(document_type)
        if not model_mapping:
            # If document type is unknown, use a generic mapping
            model_mapping = cls._MODEL_MAPPINGS.get("application_form")
            if not model_mapping:
                raise ValueError(f"Unknown document type: {document_type}")
        
        # Select model ID based on content type
        if content_type is None:
            return model_mapping["default_model_id"]
        
        if content_type == OCRModelType.TYPED:
            return model_mapping["typed_model_id"]
        elif content_type == OCRModelType.HANDWRITTEN:
            return model_mapping["handwritten_model_id"]
        elif content_type == OCRModelType.HYBRID:
            return model_mapping["hybrid_model_id"]
        else:
            return model_mapping["default_model_id"]
    
    @classmethod
    def detect_content_type(cls, image: Any) -> OCRModelType:
        """Detect the content type of an image (typed, handwritten, hybrid).
        
        This is a placeholder for a more sophisticated content type detection algorithm.
        In a real implementation, this would use a classifier to determine the content type.
        
        Args:
            image: Image data to analyze
            
        Returns:
            Detected content type
        """
        # This is a placeholder implementation
        # In a real implementation, this would use a classifier to determine the content type
        return OCRModelType.HYBRID
    
    @classmethod
    def register_model_mapping(cls, document_type: str, mapping: Dict[str, str]) -> None:
        """Register a new model mapping for a document type.
        
        Args:
            document_type: Type of document
            mapping: Model mapping dictionary
            
        Raises:
            ValueError: If the mapping is invalid
        """
        required_keys = ["typed_model_id", "handwritten_model_id", "hybrid_model_id", "default_model_id"]
        for key in required_keys:
            if key not in mapping:
                raise ValueError(f"Invalid model mapping: missing required key '{key}'")
        
        cls._MODEL_MAPPINGS[document_type] = mapping


class TensorFlowModel:
    """Wrapper for TensorFlow models used in OCR processing.
    
    This class provides a consistent interface for loading, using, and managing
    TensorFlow models for OCR processing, with support for GPU acceleration.
    
    Attributes:
        model_id: Unique identifier for the model
        model_type: Type of OCR model
        model_path: Path to the model files
        parameters: Model parameters
        is_loaded: Whether the model is currently loaded
        model: The underlying TensorFlow model (if loaded)
    """
    
    def __init__(self, model_id: str, model_type: OCRModelType, model_path: Union[str, Path], 
                parameters: ModelParameters):
        """Initialize a TensorFlow model wrapper.
        
        Args:
            model_id: Unique identifier for the model
            model_type: Type of OCR model
            model_path: Path to the model files
            parameters: Model parameters
        """
        self.model_id = model_id
        self.model_type = model_type
        self.model_path = Path(model_path)
        self.parameters = parameters
        self.is_loaded = False
        self.model = None
    
    def load(self) -> bool:
        """Load the TensorFlow model.
        
        Returns:
            True if the model was loaded successfully, False otherwise
        """
        if self.is_loaded:
            return True
        
        try:
            # Import TensorFlow here to avoid dependency at module level
            import tensorflow as tf
            
            # Configure GPU memory growth to avoid allocating all memory at once
            if self.parameters.use_gpu:
                gpus = tf.config.experimental.list_physical_devices('GPU')
                if gpus:
                    for gpu in gpus:
                        tf.config.experimental.set_memory_growth(gpu, True)
                    
                    # Set memory limit if specified
                    if self.parameters.gpu_memory_limit is not None:
                        tf.config.experimental.set_virtual_device_configuration(
                            gpus[0],
                            [tf.config.experimental.VirtualDeviceConfiguration(
                                memory_limit=self.parameters.gpu_memory_limit
                            )]
                        )
            else:
                # Disable GPU if not requested
                tf.config.set_visible_devices([], 'GPU')
            
            # Load the model
            self.model = tf.keras.models.load_model(str(self.model_path))
            self.is_loaded = True
            return True
        except Exception as e:
            # Log the error
            print(f"Failed to load TensorFlow model: {str(e)}")
            return False
    
    def unload(self) -> None:
        """Unload the TensorFlow model to free resources."""
        if not self.is_loaded:
            return
        
        try:
            # Import TensorFlow here to avoid dependency at module level
            import tensorflow as tf
            
            # Clear the model
            self.model = None
            self.is_loaded = False
            
            # Clear TensorFlow session
            tf.keras.backend.clear_session()
        except Exception as e:
            # Log the error
            print(f"Failed to unload TensorFlow model: {str(e)}")
    
    def predict(self, image: Any) -> ModelResult:
        """Run inference on an image.
        
        Args:
            image: Image data to process
            
        Returns:
            ModelResult containing the extracted text and metadata
        """
        if not self.is_loaded:
            if not self.load():
                return ModelResult.error_result(
                    model_id=self.model_id,
                    model_type=self.model_type,
                    error_message="Failed to load model"
                )
        
        try:
            # Import TensorFlow here to avoid dependency at module level
            import tensorflow as tf
            import numpy as np
            
            # Record start time
            start_time = time.time()
            
            # Preprocess image (implementation depends on model requirements)
            # This is a simplified example
            if isinstance(image, np.ndarray):
                # Resize image to model input dimensions
                image = tf.image.resize(
                    image, 
                    [self.parameters.image_height, self.parameters.image_width]
                )
                
                # Normalize pixel values to [0, 1]
                image = image / 255.0
                
                # Add batch dimension if needed
                if len(image.shape) == 3:
                    image = tf.expand_dims(image, axis=0)
            
            # Run inference
            prediction = self.model(image, training=False)
            
            # Postprocess prediction (implementation depends on model architecture)
            # This is a simplified example
            text = "Sample extracted text"  # Replace with actual text extraction
            
            # Calculate processing time
            time_ms = (time.time() - start_time) * 1000
            
            # Calculate confidence (implementation depends on model architecture)
            # This is a simplified example
            confidence = 0.95  # Replace with actual confidence calculation
            
            # Create word confidences (implementation depends on model architecture)
            # This is a simplified example
            word_confidences = {"sample": 0.95, "extracted": 0.92, "text": 0.98}
            
            return ModelResult(
                model_id=self.model_id,
                model_type=self.model_type,
                text=text,
                confidence=confidence,
                word_confidences=word_confidences,
                processing_time_ms=time_ms,
                image_dimensions=(self.parameters.image_width, self.parameters.image_height)
            )
        except Exception as e:
            return ModelResult.error_result(
                model_id=self.model_id,
                model_type=self.model_type,
                error_message=f"Prediction error: {str(e)}"
            )