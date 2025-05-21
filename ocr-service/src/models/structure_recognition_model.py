#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Structure Recognition Model for OCR Service

This module implements a TensorFlow model for recognizing and analyzing document structure,
including forms, tables, sections, and field relationships. The model identifies the semantic
structure of documents to provide context for extracted text, which is critical for understanding
the meaning and relationships of extracted data.

The model uses a combination of convolutional neural networks and transformer architecture
to identify structural elements and their relationships within documents.

Classes:
    StructureRecognitionModel: Main class for document structure recognition

Functions:
    load_model: Loads a pre-trained structure recognition model
    preprocess_image: Preprocesses an image for structure recognition
    postprocess_results: Processes model outputs into structured data

Requirements:
    - TensorFlow 2.15.0 with GPU acceleration
    - 99% data extraction accuracy
    - JSON output with field relationships
"""

import os
import json
import logging
from typing import Dict, List, Tuple, Optional, Union, Any

import numpy as np
import tensorflow as tf

from ..types.models import ModelParameters, ModelResult
from ..types.extraction import ExtractedData, FieldLocation, ExtractionMetadata
from ..types.documents import DocumentType
from ..utils.tensorflow_utils import configure_gpu_memory
from .base_model import BaseOCRModel


class StructureRecognitionModel(BaseOCRModel):
    """
    TensorFlow model for document structure recognition and analysis.
    
    This model identifies forms, tables, sections, and field relationships in documents
    to provide context for extracted text. It's critical for understanding the meaning
    and relationships of extracted data.
    
    Attributes:
        model: TensorFlow model for structure recognition
        input_shape: Expected input shape for the model
        confidence_threshold: Minimum confidence threshold for structure detection
        model_params: Additional model parameters
        field_types: Dictionary of supported field types and their characteristics
        structure_types: List of supported document structure types
    """
    
    def __init__(self, model_path: str, params: ModelParameters = None):
        """
        Initialize the structure recognition model.
        
        Args:
            model_path: Path to the pre-trained TensorFlow model
            params: Model parameters including confidence thresholds and GPU settings
        """
        super().__init__(model_path, params)
        
        # Configure GPU memory if available
        configure_gpu_memory()
        
        # Default parameters if none provided
        if params is None:
            params = ModelParameters(
                confidence_threshold=0.75,
                gpu_enabled=True,
                batch_size=1,
                model_type="structure_recognition"
            )
        
        self.model_params = params
        self.confidence_threshold = params.confidence_threshold
        
        # Load the TensorFlow model
        try:
            self.model = tf.saved_model.load(model_path)
            self.input_shape = self.model.signatures["serving_default"].inputs[0].shape.as_list()
            logging.info(f"Structure recognition model loaded successfully from {model_path}")
        except Exception as e:
            logging.error(f"Failed to load structure recognition model: {str(e)}")
            raise
        
        # Define supported field types and their characteristics
        self.field_types = {
            "text": {"type": "string", "multi_line": False},
            "paragraph": {"type": "string", "multi_line": True},
            "checkbox": {"type": "boolean", "multi_line": False},
            "signature": {"type": "image", "multi_line": False},
            "date": {"type": "date", "multi_line": False},
            "number": {"type": "numeric", "multi_line": False},
            "table_cell": {"type": "string", "multi_line": False},
            "table_header": {"type": "string", "multi_line": False},
            "list_item": {"type": "string", "multi_line": False},
            "key_value": {"type": "key_value_pair", "multi_line": False},
        }
        
        # Define supported structure types
        self.structure_types = [
            "form",
            "table",
            "section",
            "header",
            "footer",
            "list",
            "paragraph",
            "page_number",
        ]
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess the input image for structure recognition.
        
        Args:
            image: Input image as numpy array (H, W, C)
            
        Returns:
            Preprocessed image ready for model inference
        """
        # Resize image to match model input shape
        target_height, target_width = self.input_shape[1:3]
        
        # Preserve aspect ratio
        height, width = image.shape[:2]
        scale = min(target_height / height, target_width / width)
        new_height, new_width = int(height * scale), int(width * scale)
        
        # Resize the image
        resized_image = tf.image.resize(image, [new_height, new_width])
        
        # Create a blank canvas of target size
        preprocessed_image = tf.zeros([target_height, target_width, 3], dtype=tf.float32)
        
        # Place the resized image on the canvas (centered)
        offset_height = (target_height - new_height) // 2
        offset_width = (target_width - new_width) // 2
        preprocessed_image = tf.tensor_scatter_nd_update(
            preprocessed_image,
            [[h + offset_height, w + offset_width] for h in range(new_height) for w in range(new_width)],
            tf.reshape(resized_image, [-1, 3])
        )
        
        # Normalize pixel values to [0, 1]
        preprocessed_image = preprocessed_image / 255.0
        
        # Add batch dimension
        preprocessed_image = tf.expand_dims(preprocessed_image, 0)
        
        return preprocessed_image
    
    def detect_structure(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Detect document structure elements in the image.
        
        Args:
            image: Preprocessed image as numpy array
            
        Returns:
            Dictionary containing detected structure elements and their relationships
        """
        # Ensure image is properly preprocessed
        if len(image.shape) == 3:  # Add batch dimension if not present
            image = np.expand_dims(image, axis=0)
        
        # Run inference
        try:
            infer_fn = self.model.signatures["serving_default"]
            result = infer_fn(tf.constant(image, dtype=tf.float32))
            
            # Extract results from the model output
            structure_boxes = result["structure_boxes"].numpy()
            structure_scores = result["structure_scores"].numpy()
            structure_classes = result["structure_classes"].numpy()
            relationship_matrix = result["relationship_matrix"].numpy() if "relationship_matrix" in result else None
            
            # Filter by confidence threshold
            valid_indices = np.where(structure_scores > self.confidence_threshold)[0]
            structure_boxes = structure_boxes[valid_indices]
            structure_scores = structure_scores[valid_indices]
            structure_classes = structure_classes[valid_indices]
            
            # Create structure elements dictionary
            structure_elements = []
            for i in range(len(valid_indices)):
                structure_type = self.structure_types[int(structure_classes[i])]
                structure_elements.append({
                    "id": i,
                    "type": structure_type,
                    "bbox": structure_boxes[i].tolist(),  # [x1, y1, x2, y2] format
                    "confidence": float(structure_scores[i])
                })
            
            # Process relationships if available
            relationships = []
            if relationship_matrix is not None:
                # Filter relationship matrix to only include valid indices
                filtered_matrix = relationship_matrix[valid_indices][:, valid_indices]
                
                # Extract relationships where confidence > threshold
                for i in range(len(valid_indices)):
                    for j in range(len(valid_indices)):
                        if filtered_matrix[i, j] > self.confidence_threshold:
                            relationships.append({
                                "from_id": i,
                                "to_id": j,
                                "type": "contains" if structure_elements[i]["type"] in ["form", "table", "section"] else "follows",
                                "confidence": float(filtered_matrix[i, j])
                            })
            
            return {
                "elements": structure_elements,
                "relationships": relationships
            }
            
        except Exception as e:
            logging.error(f"Error during structure detection inference: {str(e)}")
            raise
    
    def detect_form_fields(self, image: np.ndarray, structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect form fields within the document structure.
        
        Args:
            image: Input image as numpy array
            structure: Document structure from detect_structure method
            
        Returns:
            List of detected form fields with their properties
        """
        # Find form elements in the structure
        form_elements = [elem for elem in structure["elements"] if elem["type"] == "form"]
        
        if not form_elements:
            return []  # No forms detected
        
        # For each form element, detect fields
        all_fields = []
        
        for form in form_elements:
            # Extract form region from the image
            x1, y1, x2, y2 = form["bbox"]
            form_image = image[0, int(y1):int(y2), int(x1):int(x2), :]
            
            # Preprocess form image for field detection
            preprocessed_form = self.preprocess_image(form_image)
            
            # Run field detection inference
            try:
                infer_fn = self.model.signatures["field_detection"]
                result = infer_fn(tf.constant(preprocessed_form, dtype=tf.float32))
                
                # Extract results
                field_boxes = result["field_boxes"].numpy()
                field_scores = result["field_scores"].numpy()
                field_classes = result["field_classes"].numpy()
                field_labels = result["field_labels"].numpy() if "field_labels" in result else None
                
                # Filter by confidence threshold
                valid_indices = np.where(field_scores > self.confidence_threshold)[0]
                field_boxes = field_boxes[valid_indices]
                field_scores = field_scores[valid_indices]
                field_classes = field_classes[valid_indices]
                
                # Map field classes to field types
                field_type_mapping = list(self.field_types.keys())
                
                # Create field elements
                for i in range(len(valid_indices)):
                    field_type = field_type_mapping[int(field_classes[i])]
                    
                    # Adjust bounding box coordinates to original image
                    box = field_boxes[i].tolist()  # [x1, y1, x2, y2] format
                    adjusted_box = [
                        box[0] + x1,  # Adjust x1
                        box[1] + y1,  # Adjust y1
                        box[2] + x1,  # Adjust x2
                        box[3] + y1   # Adjust y2
                    ]
                    
                    # Create field entry
                    field = {
                        "id": len(all_fields) + i,
                        "form_id": form["id"],
                        "type": field_type,
                        "bbox": adjusted_box,
                        "confidence": float(field_scores[i]),
                        "properties": self.field_types[field_type]
                    }
                    
                    # Add label if available
                    if field_labels is not None:
                        field["label"] = field_labels[valid_indices[i]].decode('utf-8')
                    
                    all_fields.append(field)
                    
            except Exception as e:
                logging.error(f"Error during form field detection: {str(e)}")
                continue  # Continue with next form even if this one fails
        
        return all_fields
    
    def detect_tables(self, image: np.ndarray, structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect and analyze tables within the document structure.
        
        Args:
            image: Input image as numpy array
            structure: Document structure from detect_structure method
            
        Returns:
            List of detected tables with their cells and relationships
        """
        # Find table elements in the structure
        table_elements = [elem for elem in structure["elements"] if elem["type"] == "table"]
        
        if not table_elements:
            return []  # No tables detected
        
        # For each table element, detect cells and structure
        all_tables = []
        
        for table in table_elements:
            # Extract table region from the image
            x1, y1, x2, y2 = table["bbox"]
            table_image = image[0, int(y1):int(y2), int(x1):int(x2), :]
            
            # Preprocess table image
            preprocessed_table = self.preprocess_image(table_image)
            
            # Run table analysis inference
            try:
                infer_fn = self.model.signatures["table_analysis"]
                result = infer_fn(tf.constant(preprocessed_table, dtype=tf.float32))
                
                # Extract results
                cell_boxes = result["cell_boxes"].numpy()
                cell_scores = result["cell_scores"].numpy()
                cell_types = result["cell_types"].numpy()  # 0 for header, 1 for data
                row_indices = result["row_indices"].numpy()
                col_indices = result["col_indices"].numpy()
                
                # Filter by confidence threshold
                valid_indices = np.where(cell_scores > self.confidence_threshold)[0]
                cell_boxes = cell_boxes[valid_indices]
                cell_scores = cell_scores[valid_indices]
                cell_types = cell_types[valid_indices]
                row_indices = row_indices[valid_indices]
                col_indices = col_indices[valid_indices]
                
                # Create cells list
                cells = []
                for i in range(len(valid_indices)):
                    # Adjust bounding box coordinates to original image
                    box = cell_boxes[i].tolist()  # [x1, y1, x2, y2] format
                    adjusted_box = [
                        box[0] + x1,  # Adjust x1
                        box[1] + y1,  # Adjust y1
                        box[2] + x1,  # Adjust x2
                        box[3] + y1   # Adjust y2
                    ]
                    
                    cell = {
                        "id": i,
                        "bbox": adjusted_box,
                        "confidence": float(cell_scores[i]),
                        "is_header": bool(cell_types[i] == 0),
                        "row": int(row_indices[i]),
                        "column": int(col_indices[i])
                    }
                    cells.append(cell)
                
                # Determine table dimensions
                rows = max(row_indices) + 1 if len(row_indices) > 0 else 0
                cols = max(col_indices) + 1 if len(col_indices) > 0 else 0
                
                # Create table structure
                table_structure = {
                    "id": table["id"],
                    "bbox": table["bbox"],
                    "confidence": table["confidence"],
                    "rows": int(rows),
                    "columns": int(cols),
                    "cells": cells
                }
                
                all_tables.append(table_structure)
                
            except Exception as e:
                logging.error(f"Error during table analysis: {str(e)}")
                continue  # Continue with next table even if this one fails
        
        return all_tables
    
    def detect_sections(self, structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify document sections and their hierarchical relationships.
        
        Args:
            structure: Document structure from detect_structure method
            
        Returns:
            List of document sections with their hierarchical relationships
        """
        # Find section elements in the structure
        section_elements = [elem for elem in structure["elements"] if elem["type"] == "section"]
        
        if not section_elements:
            return []  # No sections detected
        
        # Find header elements
        header_elements = [elem for elem in structure["elements"] if elem["type"] == "header"]
        
        # Find relationships for sections
        section_relationships = [rel for rel in structure["relationships"]
                               if structure["elements"][rel["from_id"]]["type"] == "section" or
                                  structure["elements"][rel["to_id"]]["type"] == "section"]
        
        # Build section hierarchy
        sections = []
        for section in section_elements:
            # Find parent section if any
            parent_rels = [rel for rel in section_relationships 
                          if rel["to_id"] == section["id"] and 
                          structure["elements"][rel["from_id"]]["type"] == "section"]
            
            parent_id = parent_rels[0]["from_id"] if parent_rels else None
            
            # Find associated header if any
            header_rels = [rel for rel in section_relationships 
                          if rel["from_id"] == section["id"] and 
                          structure["elements"][rel["to_id"]]["type"] == "header"]
            
            header_id = header_rels[0]["to_id"] if header_rels else None
            header = header_elements[header_id] if header_id is not None and header_id < len(header_elements) else None
            
            # Create section entry
            section_entry = {
                "id": section["id"],
                "bbox": section["bbox"],
                "confidence": section["confidence"],
                "parent_id": parent_id,
                "header": header["bbox"] if header else None,
                "header_confidence": header["confidence"] if header else None
            }
            
            sections.append(section_entry)
        
        return sections
    
    def extract_structure(self, image: np.ndarray, document_type: DocumentType = None) -> Dict[str, Any]:
        """
        Extract complete document structure including forms, tables, and sections.
        
        Args:
            image: Input image as numpy array
            document_type: Optional document type for specialized processing
            
        Returns:
            Complete document structure with all elements and relationships
        """
        # Preprocess the image
        preprocessed_image = self.preprocess_image(image)
        
        # Detect basic structure
        structure = self.detect_structure(preprocessed_image)
        
        # Detect form fields
        form_fields = self.detect_form_fields(preprocessed_image, structure)
        
        # Detect tables
        tables = self.detect_tables(preprocessed_image, structure)
        
        # Detect sections
        sections = self.detect_sections(structure)
        
        # Create complete structure
        complete_structure = {
            "document_type": document_type.value if document_type else "unknown",
            "structure_elements": structure["elements"],
            "structure_relationships": structure["relationships"],
            "form_fields": form_fields,
            "tables": tables,
            "sections": sections
        }
        
        return complete_structure
    
    def process_image(self, image: np.ndarray, document_type: DocumentType = None) -> ModelResult:
        """
        Process an image to extract document structure.
        
        Args:
            image: Input image as numpy array
            document_type: Optional document type for specialized processing
            
        Returns:
            ModelResult containing extracted structure and metadata
        """
        try:
            # Extract document structure
            structure = self.extract_structure(image, document_type)
            
            # Calculate overall confidence score
            confidence_scores = [elem["confidence"] for elem in structure["structure_elements"]]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # Create metadata
            metadata = ExtractionMetadata(
                model_name="structure_recognition_model",
                model_version="1.0",
                confidence_score=avg_confidence,
                processing_time=0.0,  # Will be updated by caller
                document_type=document_type.value if document_type else "unknown"
            )
            
            # Create result
            result = ModelResult(
                success=True,
                data=structure,
                metadata=metadata,
                error=None
            )
            
            return result
            
        except Exception as e:
            logging.error(f"Error in structure recognition: {str(e)}")
            
            # Create error result
            metadata = ExtractionMetadata(
                model_name="structure_recognition_model",
                model_version="1.0",
                confidence_score=0.0,
                processing_time=0.0,  # Will be updated by caller
                document_type=document_type.value if document_type else "unknown"
            )
            
            result = ModelResult(
                success=False,
                data=None,
                metadata=metadata,
                error=str(e)
            )
            
            return result
    
    def map_field_relationships(self, structure: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Map relationships between fields in the document structure.
        
        Args:
            structure: Document structure from extract_structure method
            
        Returns:
            Dictionary mapping field IDs to lists of related field IDs
        """
        relationships = {}
        
        # Process form fields
        for field in structure["form_fields"]:
            field_id = str(field["id"])
            relationships[field_id] = []
            
            # Find fields in the same form
            same_form_fields = [f for f in structure["form_fields"] if f["form_id"] == field["form_id"] and f["id"] != field["id"]]
            
            # Add related fields based on proximity and type
            for other_field in same_form_fields:
                # Check if fields are likely related (e.g., label-value pairs)
                if self._are_fields_related(field, other_field):
                    relationships[field_id].append(str(other_field["id"]))
        
        # Process table cells
        for table in structure["tables"]:
            for cell in table["cells"]:
                cell_id = f"table_{table['id']}_cell_{cell['id']}"
                relationships[cell_id] = []
                
                # Add relationships with cells in the same row
                same_row_cells = [c for c in table["cells"] if c["row"] == cell["row"] and c["id"] != cell["id"]]
                for row_cell in same_row_cells:
                    relationships[cell_id].append(f"table_{table['id']}_cell_{row_cell['id']}")
                
                # Add relationships with cells in the same column
                same_col_cells = [c for c in table["cells"] if c["column"] == cell["column"] and c["id"] != cell["id"]]
                for col_cell in same_col_cells:
                    relationships[cell_id].append(f"table_{table['id']}_cell_{col_cell['id']}")
                
                # Add relationship with header cell if this is a data cell
                if not cell["is_header"]:
                    header_cells = [c for c in table["cells"] if c["is_header"] and c["column"] == cell["column"]]
                    for header_cell in header_cells:
                        relationships[cell_id].append(f"table_{table['id']}_cell_{header_cell['id']}")
        
        return relationships
    
    def _are_fields_related(self, field1: Dict[str, Any], field2: Dict[str, Any]) -> bool:
        """
        Determine if two form fields are related based on proximity and type.
        
        Args:
            field1: First field dictionary
            field2: Second field dictionary
            
        Returns:
            True if fields are likely related, False otherwise
        """
        # Check if one is a label and one is a value field
        if field1["type"] == "key_value" and field2["type"] != "key_value":
            return True
        if field2["type"] == "key_value" and field1["type"] != "key_value":
            return True
        
        # Check proximity (fields close to each other are likely related)
        box1 = field1["bbox"]
        box2 = field2["bbox"]
        
        # Calculate centers
        center1_x = (box1[0] + box1[2]) / 2
        center1_y = (box1[1] + box1[3]) / 2
        center2_x = (box2[0] + box2[2]) / 2
        center2_y = (box2[1] + box2[3]) / 2
        
        # Calculate distance
        distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5
        
        # Calculate average field size
        size1 = ((box1[2] - box1[0]) + (box1[3] - box1[1])) / 2
        size2 = ((box2[2] - box2[0]) + (box2[3] - box2[1])) / 2
        avg_size = (size1 + size2) / 2
        
        # Fields are related if they are close to each other relative to their size
        return distance < avg_size * 3  # Threshold can be adjusted


def load_model(model_path: str, params: ModelParameters = None) -> StructureRecognitionModel:
    """
    Load a pre-trained structure recognition model.
    
    Args:
        model_path: Path to the pre-trained model
        params: Model parameters
        
    Returns:
        Initialized StructureRecognitionModel
    """
    return StructureRecognitionModel(model_path, params)