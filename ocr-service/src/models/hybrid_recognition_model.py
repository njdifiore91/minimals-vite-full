"""
Hybrid Recognition Model for OCR Service.

This module implements a combined TensorFlow model that can process documents
containing both typed and handwritten text. It intelligently switches between
typed and handwritten recognition algorithms based on text region classification.
This model is essential for processing mixed-format documents like partially
completed application forms.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime

import numpy as np
import tensorflow as tf

# Import type definitions
from src.types.models import ModelParameters, ModelResult, OCRModelType, TensorFlowModel
from src.types.extraction import ConfidenceScore, ExtractedData, ExtractedField, FieldLocation, FieldType

# Import configuration
from src.config import tensorflow_config

# Setup logging
logger = logging.getLogger(__name__)


class TextRegionClassifier:
    """
    Classifier for determining whether a text region contains typed or handwritten text.
    
    This class provides methods to analyze image regions and classify them as containing
    either typed or handwritten text, enabling the hybrid model to apply the appropriate
    recognition algorithm to each region.
    """
    
    def __init__(self, model_path: str, confidence_threshold: float = 0.75):
        """
        Initialize the text region classifier.
        
        Args:
            model_path: Path to the TensorFlow model for text region classification
            confidence_threshold: Threshold for classification confidence (default: 0.75)
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self._load_model()
    
    def _load_model(self) -> None:
        """
        Load the text region classification model from the specified path.
        
        Raises:
            RuntimeError: If the model cannot be loaded
        """
        try:
            # Configure GPU memory growth to avoid OOM errors
            gpus = tf.config.experimental.list_physical_devices('GPU')
            if gpus:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
            
            # Load the model
            self.model = tf.keras.models.load_model(self.model_path)
            logger.info(f"Loaded text region classification model from {self.model_path}")
        except Exception as e:
            error_msg = f"Error loading text region classification model: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def classify_region(self, image_region: np.ndarray) -> Tuple[str, float]:
        """
        Classify a text region as typed or handwritten.
        
        Args:
            image_region: Image region as a numpy array
            
        Returns:
            A tuple of (classification_result, confidence_score)
            where classification_result is either 'typed' or 'handwritten'
        
        Raises:
            RuntimeError: If classification fails
        """
        if self.model is None:
            raise RuntimeError("Text region classification model not loaded")
        
        try:
            # Preprocess the image region
            preprocessed = self._preprocess_region(image_region)
            
            # Run inference
            prediction = self.model.predict(preprocessed, verbose=0)
            
            # Process the prediction
            # Assuming the model outputs a single value between 0 and 1,
            # where values closer to 0 indicate typed text and values closer to 1 indicate handwritten text
            typed_score = 1.0 - prediction[0][0]
            handwritten_score = prediction[0][0]
            
            if handwritten_score > typed_score:
                return ('handwritten', float(handwritten_score))
            else:
                return ('typed', float(typed_score))
        except Exception as e:
            error_msg = f"Error classifying text region: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _preprocess_region(self, image_region: np.ndarray) -> np.ndarray:
        """
        Preprocess an image region for classification.
        
        Args:
            image_region: Image region as a numpy array
            
        Returns:
            Preprocessed image region ready for model input
        """
        # Resize to expected input size (e.g., 224x224)
        resized = tf.image.resize(image_region, [224, 224])
        
        # Normalize pixel values to [0, 1]
        normalized = resized / 255.0
        
        # Add batch dimension
        batched = tf.expand_dims(normalized, 0)
        
        return batched


class TextRegion:
    """
    Represents a region of text in a document image.
    
    This class encapsulates a region of text, its classification (typed or handwritten),
    and the confidence of that classification. It's used by the hybrid model to track
    different text regions within a document.
    """
    
    def __init__(self, image: np.ndarray, bounding_box: Dict[str, float], 
                 text_type: str = None, confidence: float = None):
        """
        Initialize a text region.
        
        Args:
            image: Image array of the text region
            bounding_box: Dictionary with 'top', 'left', 'bottom', 'right' coordinates (normalized 0-1)
            text_type: Type of text ('typed' or 'handwritten'), if known
            confidence: Confidence score for the text type classification, if known
        """
        self.image = image
        self.bounding_box = bounding_box
        self.text_type = text_type
        self.confidence = confidence
        self.extracted_text = None
        self.text_confidence = None
    
    def to_field_location(self, page: int = 0) -> FieldLocation:
        """
        Convert the bounding box to a FieldLocation.
        
        Args:
            page: Page number (default: 0)
            
        Returns:
            FieldLocation object representing this region's position
        """
        width = self.bounding_box['right'] - self.bounding_box['left']
        height = self.bounding_box['bottom'] - self.bounding_box['top']
        
        return {
            'page': page,
            'top': self.bounding_box['top'],
            'left': self.bounding_box['left'],
            'bottom': self.bounding_box['bottom'],
            'right': self.bounding_box['right'],
            'width': width,
            'height': height
        }


class HybridRecognitionModel:
    """
    Combined TensorFlow model for processing documents with both typed and handwritten text.
    
    This model intelligently switches between typed and handwritten recognition algorithms
    based on text region classification. It's essential for processing mixed-format documents
    like partially completed application forms.
    """
    
    def __init__(self, parameters: ModelParameters):
        """
        Initialize the hybrid recognition model.
        
        Args:
            parameters: Model parameters for configuration
        """
        self.parameters = parameters
        self.typed_model = None
        self.handwritten_model = None
        self.region_classifier = None
        self.region_detector = None
        self._initialize_models()
    
    def _initialize_models(self) -> None:
        """
        Initialize all component models needed for hybrid recognition.
        
        This includes:
        - Text region detector (for segmenting text regions)
        - Text region classifier (for determining text type)
        - Typed text recognition model
        - Handwritten text recognition model
        
        Raises:
            RuntimeError: If any model fails to initialize
        """
        try:
            # Configure GPU memory growth to avoid OOM errors
            gpus = tf.config.experimental.list_physical_devices('GPU')
            if gpus:
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
            
            # Load text region detector model
            region_detector_path = tensorflow_config.get_model_path('text_region_detector')
            self.region_detector = tf.keras.models.load_model(region_detector_path)
            logger.info(f"Loaded text region detector model from {region_detector_path}")
            
            # Initialize text region classifier
            region_classifier_path = tensorflow_config.get_model_path('text_region_classifier')
            self.region_classifier = TextRegionClassifier(
                model_path=region_classifier_path,
                confidence_threshold=self.parameters.get('confidence_threshold', 0.75)
            )
            logger.info(f"Initialized text region classifier from {region_classifier_path}")
            
            # Load typed text model
            typed_model_path = tensorflow_config.get_model_path('typed_text_model')
            self.typed_model = tf.keras.models.load_model(typed_model_path)
            logger.info(f"Loaded typed text model from {typed_model_path}")
            
            # Load handwritten text model
            handwritten_model_path = tensorflow_config.get_model_path('handwritten_text_model')
            self.handwritten_model = tf.keras.models.load_model(handwritten_model_path)
            logger.info(f"Loaded handwritten text model from {handwritten_model_path}")
            
        except Exception as e:
            error_msg = f"Error initializing hybrid recognition model: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def detect_text_regions(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect text regions in an image.
        
        Args:
            image: Document image as a numpy array
            
        Returns:
            List of dictionaries containing bounding box coordinates for text regions
            
        Raises:
            RuntimeError: If region detection fails
        """
        if self.region_detector is None:
            raise RuntimeError("Text region detector model not loaded")
        
        try:
            # Preprocess the image for region detection
            preprocessed = self._preprocess_image(image)
            
            # Run inference to detect text regions
            detection_result = self.region_detector.predict(preprocessed, verbose=0)
            
            # Process the detection result to extract bounding boxes
            # The exact format depends on the model architecture (e.g., YOLO, SSD, Faster R-CNN)
            # This is a simplified example assuming the model outputs bounding boxes directly
            bounding_boxes = self._process_detection_result(detection_result, image.shape)
            
            return bounding_boxes
        except Exception as e:
            error_msg = f"Error detecting text regions: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _process_detection_result(self, detection_result: Any, image_shape: Tuple[int, ...]) -> List[Dict[str, Any]]:
        """
        Process detection results to extract bounding boxes.
        
        Args:
            detection_result: Raw output from the region detector model
            image_shape: Shape of the original image
            
        Returns:
            List of dictionaries containing normalized bounding box coordinates
        """
        # This is a simplified implementation
        # The actual implementation would depend on the specific model architecture used
        height, width = image_shape[:2]
        bounding_boxes = []
        
        # Assuming detection_result contains boxes, scores, and classes
        boxes = detection_result['boxes'][0] if isinstance(detection_result, dict) else detection_result[0]
        scores = detection_result['scores'][0] if isinstance(detection_result, dict) else detection_result[1]
        
        # Filter by confidence threshold
        confidence_threshold = self.parameters.get('detection_confidence_threshold', 0.5)
        
        for i, score in enumerate(scores):
            if score >= confidence_threshold:
                # Get coordinates (assumed to be in [y1, x1, y2, x2] format)
                y1, x1, y2, x2 = boxes[i]
                
                # Normalize coordinates to [0, 1] range
                bounding_box = {
                    'top': float(y1 / height),
                    'left': float(x1 / width),
                    'bottom': float(y2 / height),
                    'right': float(x2 / width),
                    'confidence': float(score)
                }
                
                bounding_boxes.append(bounding_box)
        
        return bounding_boxes
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess an image for model input.
        
        Args:
            image: Input image as a numpy array
            
        Returns:
            Preprocessed image ready for model input
        """
        # Resize if needed
        if self.parameters.get('input_shape'):
            height, width, _ = self.parameters['input_shape']
            resized = tf.image.resize(image, [height, width])
        else:
            resized = image
        
        # Convert to grayscale if needed
        if self.parameters.get('grayscale', False) and resized.shape[-1] == 3:
            grayscale = tf.image.rgb_to_grayscale(resized)
            # Expand back to 3 channels if the model expects it
            if self.parameters.get('input_shape') and self.parameters['input_shape'][-1] == 3:
                processed = tf.tile(grayscale, [1, 1, 3])
            else:
                processed = grayscale
        else:
            processed = resized
        
        # Normalize if needed
        if self.parameters.get('normalize_input', True):
            processed = processed / 255.0
        
        # Add batch dimension
        batched = tf.expand_dims(processed, 0)
        
        return batched
    
    def extract_text_from_region(self, region: TextRegion) -> Tuple[str, float]:
        """
        Extract text from a text region using the appropriate model.
        
        Args:
            region: TextRegion object containing the image and metadata
            
        Returns:
            Tuple of (extracted_text, confidence_score)
            
        Raises:
            RuntimeError: If text extraction fails
        """
        # If region type is not determined, classify it
        if region.text_type is None:
            region.text_type, region.confidence = self.region_classifier.classify_region(region.image)
        
        try:
            # Select the appropriate model based on text type
            if region.text_type == 'handwritten':
                if self.handwritten_model is None:
                    raise RuntimeError("Handwritten text model not loaded")
                
                # Preprocess for handwritten model
                preprocessed = self._preprocess_for_handwritten(region.image)
                
                # Extract text using handwritten model
                result = self.handwritten_model.predict(preprocessed, verbose=0)
                text, confidence = self._decode_handwritten_result(result)
            else:  # typed text
                if self.typed_model is None:
                    raise RuntimeError("Typed text model not loaded")
                
                # Preprocess for typed model
                preprocessed = self._preprocess_for_typed(region.image)
                
                # Extract text using typed model
                result = self.typed_model.predict(preprocessed, verbose=0)
                text, confidence = self._decode_typed_result(result)
            
            return text, confidence
        except Exception as e:
            error_msg = f"Error extracting text from region: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _preprocess_for_typed(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess an image for the typed text model.
        
        Args:
            image: Image region as a numpy array
            
        Returns:
            Preprocessed image ready for typed text model input
        """
        # Apply specific preprocessing for typed text
        # This might include different resizing, normalization, etc.
        # For simplicity, we'll use the same preprocessing as the general method
        return self._preprocess_image(image)
    
    def _preprocess_for_handwritten(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess an image for the handwritten text model.
        
        Args:
            image: Image region as a numpy array
            
        Returns:
            Preprocessed image ready for handwritten text model input
        """
        # Apply specific preprocessing for handwritten text
        # This might include different resizing, normalization, etc.
        # For simplicity, we'll use the same preprocessing as the general method
        return self._preprocess_image(image)
    
    def _decode_typed_result(self, result: Any) -> Tuple[str, float]:
        """
        Decode the result from the typed text model.
        
        Args:
            result: Raw output from the typed text model
            
        Returns:
            Tuple of (decoded_text, confidence_score)
        """
        # This is a simplified implementation
        # The actual implementation would depend on the specific model architecture used
        # For example, for a CTC-based model, you would use a CTC decoder
        
        # Assuming the model outputs character probabilities and we need to decode them
        # This is just a placeholder implementation
        if isinstance(result, dict) and 'text' in result and 'confidence' in result:
            return result['text'], result['confidence']
        
        # For a more realistic implementation, you might have something like:
        # decoded_text = ctc_decoder.decode(result['logits'])
        # confidence = calculate_confidence(result['logits'])
        
        # Simplified placeholder
        decoded_text = "Sample typed text"
        confidence = 0.95
        
        return decoded_text, confidence
    
    def _decode_handwritten_result(self, result: Any) -> Tuple[str, float]:
        """
        Decode the result from the handwritten text model.
        
        Args:
            result: Raw output from the handwritten text model
            
        Returns:
            Tuple of (decoded_text, confidence_score)
        """
        # This is a simplified implementation
        # The actual implementation would depend on the specific model architecture used
        # Handwritten text recognition often requires more complex decoding
        
        # Assuming the model outputs character probabilities and we need to decode them
        # This is just a placeholder implementation
        if isinstance(result, dict) and 'text' in result and 'confidence' in result:
            return result['text'], result['confidence']
        
        # For a more realistic implementation, you might have something like:
        # decoded_text = attention_decoder.decode(result['logits'])
        # confidence = calculate_confidence(result['logits'])
        
        # Simplified placeholder
        decoded_text = "Sample handwritten text"
        confidence = 0.85
        
        return decoded_text, confidence
    
    def process_document(self, image: np.ndarray, document_type: str = None) -> ExtractedData:
        """
        Process a document image using the hybrid recognition model.
        
        This is the main entry point for document processing. It detects text regions,
        classifies them as typed or handwritten, extracts text using the appropriate models,
        and returns structured data.
        
        Args:
            image: Document image as a numpy array
            document_type: Type of document, if known (optional)
            
        Returns:
            ExtractedData containing the structured extraction results
            
        Raises:
            RuntimeError: If document processing fails
        """
        start_time = time.time()
        extraction_id = str(uuid.uuid4())
        
        try:
            # Step 1: Detect text regions in the document
            logger.info(f"Detecting text regions in document {extraction_id}")
            bounding_boxes = self.detect_text_regions(image)
            
            # Step 2: Create TextRegion objects for each detected region
            text_regions = []
            for bbox in bounding_boxes:
                # Extract the region from the image
                top = int(bbox['top'] * image.shape[0])
                left = int(bbox['left'] * image.shape[1])
                bottom = int(bbox['bottom'] * image.shape[0])
                right = int(bbox['right'] * image.shape[1])
                
                region_image = image[top:bottom, left:right]
                text_regions.append(TextRegion(region_image, bbox))
            
            # Step 3: Classify each region as typed or handwritten
            logger.info(f"Classifying {len(text_regions)} text regions")
            for region in text_regions:
                region.text_type, region.confidence = self.region_classifier.classify_region(region.image)
            
            # Step 4: Extract text from each region using the appropriate model
            logger.info(f"Extracting text from regions")
            extracted_fields = {}
            low_confidence_fields = []
            raw_text_parts = []
            
            for i, region in enumerate(text_regions):
                # Extract text using the appropriate model
                text, confidence = self.extract_text_from_region(region)
                region.extracted_text = text
                region.text_confidence = confidence
                
                # Add to raw text
                raw_text_parts.append(text)
                
                # Create field name (this would be more sophisticated in a real implementation)
                field_name = f"field_{i+1}"
                
                # Create extracted field
                field_location = region.to_field_location(page=0)
                confidence_score = ConfidenceScore.from_float(confidence)
                
                extracted_field = {
                    'field_name': field_name,
                    'field_type': FieldType.TEXT.value,
                    'value': text,
                    'raw_text': text,
                    'confidence': confidence_score,
                    'location': field_location,
                    'alternatives': [],  # Would contain alternative recognitions in a real implementation
                    'metadata': {
                        'text_type': region.text_type,
                        'classification_confidence': region.confidence
                    },
                    'requires_verification': confidence < self.parameters.get('confidence_threshold', 0.7),
                    'verification_reason': 'Low confidence' if confidence < self.parameters.get('confidence_threshold', 0.7) else None,
                    'extraction_timestamp': datetime.now()
                }
                
                extracted_fields[field_name] = extracted_field
                
                # Check if this is a low confidence field
                if confidence < self.parameters.get('confidence_threshold', 0.7):
                    low_confidence_fields.append(field_name)
            
            # Step 5: Prepare the extraction result
            processing_time = time.time() - start_time
            
            # Create extraction metadata
            metadata = {
                'extraction_id': extraction_id,
                'document_id': extraction_id,  # In a real implementation, this would be provided
                'model_id': self.parameters.get('model_name', 'hybrid_text_ocr'),
                'model_version': self.parameters.get('model_version', '1.0.0'),
                'document_type': document_type or 'unknown',
                'page_count': 1,  # Assuming single page for simplicity
                'language': self.parameters.get('language', 'en'),
                'processing_node': 'node-1',  # In a real implementation, this would be dynamic
                'extraction_status': 'success',
                'processing_time': processing_time,
                'warnings': [],
                'errors': []
            }
            
            # Create the final extraction result
            extraction_result = {
                'extraction_id': extraction_id,
                'fields': extracted_fields,
                'tables': [],  # Would contain table data in a real implementation
                'metadata': metadata,
                'raw_text': '\n'.join(raw_text_parts),
                'low_confidence_fields': low_confidence_fields,
                'requires_verification': len(low_confidence_fields) > 0,
                'extraction_timestamp': datetime.now(),
                'schema_version': '1.0',
                'document_type': document_type or 'unknown'
            }
            
            logger.info(f"Document processing completed in {processing_time:.2f} seconds")
            return extraction_result
        
        except Exception as e:
            error_msg = f"Error processing document: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)


class HybridRecognitionModelFactory:
    """
    Factory class for creating HybridRecognitionModel instances.
    
    This class provides methods for creating and configuring HybridRecognitionModel
    instances with appropriate parameters based on document types and processing requirements.
    """
    
    @staticmethod
    def create_model(document_type: str = None, custom_parameters: Dict[str, Any] = None) -> HybridRecognitionModel:
        """
        Create a HybridRecognitionModel instance with appropriate parameters.
        
        Args:
            document_type: Type of document to process (optional)
            custom_parameters: Custom parameters to override defaults (optional)
            
        Returns:
            Configured HybridRecognitionModel instance
        """
        # Start with default parameters
        parameters = dict(tensorflow_config.DEFAULT_HYBRID_MODEL_PARAMS)
        
        # Adjust parameters based on document type if specified
        if document_type:
            if document_type == 'application_form':
                # Application forms often have more handwritten content
                parameters.update({
                    'confidence_threshold': 0.65,  # Lower threshold for application forms
                    'detection_confidence_threshold': 0.4,  # More aggressive region detection
                    'gpu_memory_limit': 8192,  # 8GB for complex forms
                })
            elif document_type == 'tax_return':
                # Tax returns are mostly typed with some handwritten sections
                parameters.update({
                    'confidence_threshold': 0.75,  # Higher threshold for tax documents
                    'detection_confidence_threshold': 0.5,
                    'gpu_memory_limit': 6144,  # 6GB is sufficient
                })
            elif document_type == 'bank_statement':
                # Bank statements are mostly typed with tabular data
                parameters.update({
                    'confidence_threshold': 0.8,  # Higher threshold for structured documents
                    'detection_confidence_threshold': 0.6,
                    'gpu_memory_limit': 4096,  # 4GB is sufficient
                })
        
        # Override with any custom parameters
        if custom_parameters:
            parameters.update(custom_parameters)
        
        # Create and return the model
        return HybridRecognitionModel(parameters)